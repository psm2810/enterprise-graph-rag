"""Central configuration, loaded from environment (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "supplychain")

    # Chat provider: "ollama" (local) or "groq" (cloud, for Render deploy).
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()

    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:3b-instruct")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Groq (used when LLM_PROVIDER=groq).
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Embedding backend: "ollama" (nomic-embed-text) or "fastembed" (local ONNX,
    # used for cloud deploy where Ollama is unavailable).
    embed_provider: str = os.getenv("EMBED_PROVIDER", "ollama").lower()
    fastembed_model: str = os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")

    top_k: int = int(os.getenv("TOP_K", "6"))
    max_hops: int = int(os.getenv("MAX_HOPS", "4"))

    # PDF ingestion guardrails (keep memory / setup bounded)
    pdf_max_mb: float = float(os.getenv("PDF_MAX_MB", "5"))
    pdf_max_chunks: int = int(os.getenv("PDF_MAX_CHUNKS", "20"))
    pdf_max_nodes: int = int(os.getenv("PDF_MAX_NODES", "30"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1024"))
    # Ollama model used for extraction (defaults to the main LLM; can override to
    # a stronger model like llama3.1:8b just for ingestion if quality is low).
    extract_model: str = os.getenv("EXTRACT_MODEL", os.getenv("LLM_MODEL", "qwen2.5:3b-instruct"))
    # Groq model used for extraction (a faster/cheaper model is fine here).
    groq_extract_model: str = os.getenv("GROQ_EXTRACT_MODEL", "llama-3.1-8b-instant")


settings = Settings()
