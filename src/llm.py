"""Ollama LLM and embedding helpers."""

from __future__ import annotations

import ollama as _ollama

from config.settings import settings


def embed(text: str) -> list[float]:
    """Return embedding vector for *text* using the configured embed model."""
    resp = _ollama.embed(model=settings.embed_model, input=text)
    return resp["embeddings"][0]


def chat(prompt: str, system: str = "") -> str:
    """Single-turn chat completion with the configured LLM."""
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _ollama.chat(model=settings.llm_model, messages=messages)
    return resp["message"]["content"]
