"""Run Graph RAG against the ground-truth Q&A pairs and print a report.

Usage:
    uv run python -m src.eval
"""

from __future__ import annotations

import yaml

from src.graphrag import answer as graph_answer
from src.vector_baseline import answer_vector_only


def _load_qa() -> list[dict]:
    with open("data/eval/qa_pairs.yaml") as f:
        return yaml.safe_load(f)


def run_eval() -> None:
    qa_pairs = _load_qa()
    print(f"Running evaluation on {len(qa_pairs)} questions …\n")

    for i, qa in enumerate(qa_pairs, 1):
        q = qa["question"]
        expected = qa["expected_answer"].strip()
        difficulty = qa.get("difficulty", "?")
        print(f"{'='*70}")
        print(f"Q{i} [{difficulty}]: {q}")
        print(f"{'='*70}")

        # Graph RAG
        g = graph_answer(q)
        print(f"\n--- Graph RAG ({g['triple_count']} triples) ---")
        print(g["answer"])

        # Vector baseline
        v = answer_vector_only(q)
        print(f"\n--- Vector RAG ({v['snippet_count']} snippets) ---")
        print(v["answer"])

        print(f"\n--- Expected ---")
        print(expected)
        print()


if __name__ == "__main__":
    run_eval()
