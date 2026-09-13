"""Provider-aware LLM + embedding helpers.

Chat is routed to Ollama (local) or Groq (cloud) via ``LLM_PROVIDER``.
Embeddings are produced by Ollama (``nomic-embed-text``) or a local fastembed
model via ``EMBED_PROVIDER`` — Groq offers no embeddings API, so cloud deploys
use fastembed.
"""

from __future__ import annotations

import time

from config.settings import settings

# Lazily-initialised singletons so importing this module stays cheap and does
# not require every provider's dependency to be installed.
_groq_client = None
_fastembed_model = None


# ── chat ─────────────────────────────────────────────────────────────────

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        if not settings.groq_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add it to your environment or .env file."
            )
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def _groq_chat(messages: list[dict], model: str) -> str:
    """Call Groq chat completions with retry/backoff for rate limits."""
    from groq import APIStatusError, RateLimitError

    client = _get_groq_client()
    delay = 2.0
    last_err: Exception | None = None
    for _ in range(5):
        try:
            resp = client.chat.completions.create(model=model, messages=messages)
            return resp.choices[0].message.content or ""
        except (RateLimitError, APIStatusError) as err:
            # Retry only on 429 / 5xx; re-raise other API errors immediately.
            code = getattr(err, "status_code", None)
            if isinstance(err, RateLimitError) or (code is not None and code >= 500):
                last_err = err
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"Groq request failed after retries: {last_err}")


def _ollama_chat(messages: list[dict], model: str) -> str:
    import ollama as _ollama

    resp = _ollama.chat(model=model, messages=messages)
    return resp["message"]["content"]


def chat(prompt: str, system: str = "") -> str:
    """Single-turn chat completion with the configured provider."""
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if settings.llm_provider == "groq":
        return _groq_chat(messages, settings.groq_model)
    return _ollama_chat(messages, settings.llm_model)


# ── embeddings ───────────────────────────────────────────────────────────

def _get_fastembed_model():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding

        _fastembed_model = TextEmbedding(model_name=settings.fastembed_model)
    return _fastembed_model


def embed(text: str) -> list[float]:
    """Return an embedding vector for *text* using the configured backend."""
    if settings.embed_provider == "fastembed":
        model = _get_fastembed_model()
        return next(iter(model.embed([text]))).tolist()

    import ollama as _ollama

    resp = _ollama.embed(model=settings.embed_model, input=text)
    return resp["embeddings"][0]
