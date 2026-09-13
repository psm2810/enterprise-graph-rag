"""One-shot seed: load the supply-chain graph, then build node embeddings.

Use this to populate a fresh database (e.g. Neo4j Aura) before a deploy/demo.
It reads the active provider config from your environment / .env, so run it
with the SAME EMBED_PROVIDER you will serve with — embedding dimensions differ
between backends (ollama nomic-embed-text = 768, fastembed bge-small = 384) and
are not cross-compatible.

Usage:
    # Seed Aura for the Groq/cloud demo (fastembed embeddings):
    EMBED_PROVIDER=fastembed uv run python -m src.seed --clear

    # Seed local Docker Neo4j (Ollama embeddings):
    uv run python -m src.seed --clear
"""

from __future__ import annotations

import sys

from config.settings import settings
from src.embeddings import build_embeddings
from src.loader import load_graph


def seed(clear: bool = False) -> None:
    print(
        f"Seeding Neo4j at {settings.neo4j_uri} "
        f"(embed_provider={settings.embed_provider})\n"
    )

    load_graph(clear=clear)

    print("\nBuilding embeddings …")
    count = build_embeddings()
    print(f"Seed complete ✓  ({count} nodes embedded)")


if __name__ == "__main__":
    seed(clear="--clear" in sys.argv)
