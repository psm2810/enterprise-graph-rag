"""Build node embeddings, store on Neo4j nodes, and provide hybrid search.

Usage:
    uv run python -m src.embeddings   # build & store embeddings for all nodes
"""

from __future__ import annotations

import numpy as np

from src.db import Neo4jConnection
from src.llm import embed


# ── build & store ────────────────────────────────────────────────────────

def _embedding_text(record: dict) -> str:
    """Compose a short text block from a node's properties for embedding."""
    label = record.get("label", "")
    name = record.get("name", "")
    desc = record.get("description", "")
    _ignore = ("label", "name", "description", "embedding", "embedding_text", "source", "document")
    extras = {k: v for k, v in record.items() if k not in _ignore}
    extra_str = " ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
    return f"{label} {name}: {desc} {extra_str}".strip()


def build_embeddings(only_missing: bool = False) -> int:
    """Embed nodes and store the vector + text on each node.

    If *only_missing* is True, only nodes without an existing embedding are
    processed (used after adding PDF-derived nodes). Returns the count embedded.
    """
    where = "WHERE n.embedding IS NULL " if only_missing else ""
    with Neo4jConnection() as conn:
        rows = conn.query(
            f"MATCH (n) {where}"
            "RETURN labels(n)[0] AS label, n.name AS name, "
            "n.description AS description, properties(n) AS props"
        )
        print(f"Embedding {len(rows)} nodes …")
        for i, row in enumerate(rows):
            record = {"label": row["label"], **row["props"]}
            text = _embedding_text(record)
            vec = embed(text)
            conn.write(
                "MATCH (n {name: $name}) "
                "SET n.embedding = $vec, n.embedding_text = $text",
                {"name": row["name"], "vec": vec, "text": text},
            )
            if (i + 1) % 10 == 0 or i + 1 == len(rows):
                print(f"  {i+1}/{len(rows)}")
        print("Embeddings stored ✓")
    return len(rows)


# ── hybrid search ────────────────────────────────────────────────────────

def _cosine_sim(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a), np.asarray(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _keyword_overlap(query_tokens: set[str], text: str) -> float:
    text_tokens = set(text.lower().split())
    if not query_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


def hybrid_search(query: str, top_k: int = 6) -> list[dict]:
    """Return top-k nodes ranked by (0.7 * cosine + 0.3 * keyword_overlap)."""
    query_vec = embed(query)
    query_tokens = set(query.lower().split())

    with Neo4jConnection() as conn:
        rows = conn.query(
            "MATCH (n) WHERE n.embedding IS NOT NULL "
            "RETURN labels(n)[0] AS label, n.name AS name, "
            "n.embedding AS embedding, n.embedding_text AS embedding_text"
        )

    scored: list[tuple[float, dict]] = []
    for row in rows:
        cos = _cosine_sim(query_vec, row["embedding"])
        kw = _keyword_overlap(query_tokens, row.get("embedding_text", ""))
        score = 0.7 * cos + 0.3 * kw
        scored.append((score, {"label": row["label"], "name": row["name"], "score": round(score, 4)}))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


if __name__ == "__main__":
    build_embeddings()
