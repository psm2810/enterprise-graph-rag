"""Core Graph RAG: hybrid retrieval → subgraph traversal → grounded LLM answer."""

from __future__ import annotations

from config.settings import settings
from src.db import Neo4jConnection
from src.embeddings import hybrid_search
from src.llm import chat


# ── subgraph expansion ───────────────────────────────────────────────────

def _expand_subgraph(seed_names: list[str], max_hops: int = 4) -> list[str]:
    """From seed node names, traverse up to *max_hops* and return triples."""
    with Neo4jConnection() as conn:
        rows = conn.query(
            "UNWIND $seeds AS seed "
            "MATCH (start {name: seed}) "
            "MATCH path = (start)-[*1.." + str(max_hops) + "]-(connected) "
            "UNWIND relationships(path) AS r "
            "WITH startNode(r) AS a, type(r) AS rel, endNode(r) AS b "
            "RETURN DISTINCT "
            "  labels(a)[0] + ' \"' + a.name + '\"' AS src, "
            "  rel, "
            "  labels(b)[0] + ' \"' + b.name + '\"' AS tgt",
            {"seeds": seed_names},
        )
    return [f"{r['src']} -[{r['rel']}]-> {r['tgt']}" for r in rows]


# ── answer generation ───────────────────────────────────────────────────

_SYSTEM = (
    "You are a supply-chain risk analyst. Answer the user's question using "
    "ONLY the graph triples provided below. Cite specific entities and "
    "relationships. If the triples do not contain enough information, say so."
)


def answer(question: str, top_k: int | None = None, max_hops: int | None = None) -> dict:
    """End-to-end Graph RAG pipeline: search → expand → answer.

    Returns dict with keys: answer, seeds, triples, triple_count.
    """
    k = top_k or settings.top_k
    hops = max_hops or settings.max_hops

    # 1. Hybrid search for seed nodes
    seeds = hybrid_search(question, top_k=k)
    seed_names = [s["name"] for s in seeds]

    # 2. Expand subgraph around seeds
    triples = _expand_subgraph(seed_names, max_hops=hops)

    # 3. Build context and prompt
    context = "\n".join(triples) if triples else "(no triples found)"
    prompt = (
        f"### Graph triples (knowledge graph context)\n{context}\n\n"
        f"### Question\n{question}"
    )

    # 4. Generate grounded answer
    llm_answer = chat(prompt, system=_SYSTEM)

    return {
        "answer": llm_answer,
        "seeds": seeds,
        "triples": triples,
        "triple_count": len(triples),
    }
