"""Plain vector-RAG baseline for side-by-side comparison with Graph RAG."""

from __future__ import annotations

from src.db import Neo4jConnection
from src.embeddings import hybrid_search
from src.llm import chat

_SYSTEM = (
    "You are a supply-chain analyst. Answer the user's question using ONLY "
    "the text snippets provided below. If the snippets do not contain enough "
    "information, say so. Do NOT invent facts."
)


def answer_vector_only(question: str, top_k: int = 6) -> dict:
    """Retrieve top-k nodes by embedding similarity and answer without graph traversal."""
    seeds = hybrid_search(question, top_k=top_k)
    seed_names = [s["name"] for s in seeds]

    # Fetch only the embedding_text (no subgraph expansion)
    with Neo4jConnection() as conn:
        rows = conn.query(
            "UNWIND $names AS n "
            "MATCH (node {name: n}) "
            "RETURN node.name AS name, node.embedding_text AS text",
            {"names": seed_names},
        )

    snippets = "\n".join(f"- {r['text']}" for r in rows if r.get("text"))
    prompt = f"### Retrieved snippets\n{snippets}\n\n### Question\n{question}"

    llm_answer = chat(prompt, system=_SYSTEM)
    return {
        "answer": llm_answer,
        "seeds": seeds,
        "snippet_count": len(rows),
    }
