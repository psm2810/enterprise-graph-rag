"""Extract schema-constrained triples from a PDF using LlamaIndex + Ollama.

Pipeline: pypdf (read) -> size/chunk guardrails -> LlamaIndex SentenceSplitter
(chunk) -> LlamaIndex Ollama LLM (constrained extraction) -> typed triples that
conform to `src/schema.py`. The triples are then handed to `src/graph_writer.py`
to MERGE into the existing Neo4j graph.

Usage:
    uv run python -m src.pdf_ingest path/to/document.pdf
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Callable

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from config.settings import settings
from src.schema import ENTITY_TYPES, RELATION_TYPES, VALID_TRIPLES, is_valid_triple


def _build_extract_llm():
    """Return a LlamaIndex LLM for extraction based on the configured provider."""
    if settings.llm_provider == "groq":
        from llama_index.llms.groq import Groq

        return Groq(
            model=settings.groq_extract_model,
            api_key=settings.groq_api_key,
            request_timeout=180.0,
        )

    from llama_index.llms.ollama import Ollama

    return Ollama(
        model=settings.extract_model,
        base_url=settings.ollama_host,
        request_timeout=180.0,
    )


class PdfTooLargeError(Exception):
    """Raised when an uploaded PDF exceeds the configured size limit."""


# ── reading ──────────────────────────────────────────────────────────────

def _check_size(size_bytes: int) -> None:
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > settings.pdf_max_mb:
        raise PdfTooLargeError(
            f"PDF is {size_mb:.1f} MB, which exceeds the {settings.pdf_max_mb} MB limit."
        )


def read_pdf_text(source: str | Path | bytes) -> str:
    """Extract raw text from a PDF path or raw bytes (Streamlit upload)."""
    from pypdf import PdfReader

    if isinstance(source, (str, Path)):
        path = Path(source)
        _check_size(path.stat().st_size)
        reader = PdfReader(str(path))
    else:
        _check_size(len(source))
        reader = PdfReader(io.BytesIO(source))

    return "\n".join((page.extract_text() or "") for page in reader.pages)


# ── chunking ─────────────────────────────────────────────────────────────

def _chunk(text: str) -> list[str]:
    splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=100)
    nodes = splitter.get_nodes_from_documents([Document(text=text)])
    chunks = [n.get_content() for n in nodes]
    return chunks[: settings.pdf_max_chunks]


# ── extraction prompt ────────────────────────────────────────────────────

_ENTITY_HINTS = {
    "Region": "a geographic region or country",
    "Factory": "a manufacturing plant, fab, or foundry",
    "Supplier": "a supplier of raw materials or parts",
    "Component": "a part, chip, material, or subassembly used inside products",
    "Product": "a finished product, module, or system that is sold",
    "Customer": "a buyer, OEM, or client company",
    "RiskEvent": "a disruption, shortage, disaster, or other supply-chain risk",
}


def _valid_patterns_text() -> str:
    lines = []
    for subj, rel, obj in sorted(VALID_TRIPLES):
        lines.append(f"- ({subj}) -[{rel}]-> ({obj})")
    return "\n".join(lines)


def _extract_prompt(chunk: str) -> str:
    entity_lines = "\n".join(f"- {e}: {_ENTITY_HINTS[e]}" for e in ENTITY_TYPES)
    return (
        "You are an information-extraction engine for a supply-chain knowledge graph.\n"
        "Extract relationships from the TEXT below.\n\n"
        "Allowed entity types:\n"
        f"{entity_lines}\n\n"
        "Allowed relationship patterns (subject_type -[relation]-> object_type):\n"
        f"{_valid_patterns_text()}\n\n"
        "Rules:\n"
        "- Only output relationships that match an allowed pattern exactly.\n"
        "- Use the entity's proper name as it appears in the text.\n"
        "- Do NOT invent facts that are not stated in the text.\n"
        "- Respond with ONLY a JSON array, no prose. Each item must be:\n"
        '  {"subject": str, "subject_type": str, "relation": str, "object": str, "object_type": str}\n'
        "- If nothing matches, respond with [].\n\n"
        f"TEXT:\n{chunk}\n\n"
        "JSON:"
    )


# ── parsing / normalisation ──────────────────────────────────────────────

_ENTITY_LOOKUP = {e.lower(): e for e in ENTITY_TYPES}
_RELATION_LOOKUP = {r.lower(): r for r in RELATION_TYPES}


def _normalise_type(value: str, lookup: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        return None
    return lookup.get(value.strip().lower().replace(" ", "_"))


def _parse_json_triples(raw: str) -> list[dict]:
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        subj = str(item.get("subject", "")).strip()
        obj = str(item.get("object", "")).strip()
        subj_type = _normalise_type(item.get("subject_type", ""), _ENTITY_LOOKUP)
        obj_type = _normalise_type(item.get("object_type", ""), _ENTITY_LOOKUP)
        rel = _normalise_type(item.get("relation", ""), _RELATION_LOOKUP)
        if not (subj and obj and subj_type and obj_type and rel):
            continue
        if not is_valid_triple(subj_type, rel, obj_type):
            continue
        out.append(
            {
                "subject": subj,
                "subject_type": subj_type,
                "relation": rel,
                "object": obj,
                "object_type": obj_type,
            }
        )
    return out


# ── main entry point ─────────────────────────────────────────────────────

def extract_triples(
    source: str | Path | bytes,
    progress: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Read a PDF and return a de-duplicated list of schema-valid triples."""
    text = read_pdf_text(source)
    chunks = _chunk(text)

    llm = _build_extract_llm()

    seen: set[tuple[str, str, str]] = set()
    triples: list[dict] = []
    for i, chunk in enumerate(chunks):
        try:
            resp = llm.complete(_extract_prompt(chunk))
            parsed = _parse_json_triples(resp.text)
        except Exception:
            parsed = []
        for t in parsed:
            key = (t["subject"], t["relation"], t["object"])
            if key not in seen:
                seen.add(key)
                triples.append(t)
        if progress:
            progress(i + 1, len(chunks))
    return triples


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pdf_ingest path/to/document.pdf")
        raise SystemExit(1)
    result = extract_triples(
        sys.argv[1],
        progress=lambda done, total: print(f"  chunk {done}/{total}"),
    )
    print(f"\nExtracted {len(result)} valid triples:")
    for t in result:
        print(f'  {t["subject_type"]} "{t["subject"]}" -[{t["relation"]}]-> {t["object_type"]} "{t["object"]}"')
