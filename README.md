# Enterprise Graph RAG — Supply-Chain Risk & Impact POC

A **fully local, open-source, zero-cost** Graph RAG proof-of-concept that answers
supply-chain risk questions like:

> **"How does the chip shortage at Factory A impact our client, Acme Corp?"**

It stitches an answer across a knowledge graph that **no single document contains**,
then shows *why* plain vector RAG misses it — side by side.

## Why Graph RAG here

The flagship chain is deliberately spread across many records:

```
RiskEvent "Chip Shortage at Factory A"
   └─AFFECTS→ Factory "Factory A"
        └─PRODUCES→ Component "NX-7 Microcontroller"
             └─USED_IN→ Product "DriveECU-500"
                  └─SOLD_TO→ Customer "Acme Corp"
```

No single row/document links the chip shortage to Acme Corp. A vector store retrieves
loosely-related text and guesses; the graph **traverses the actual dependency path**
and grounds the LLM on real triples with citations.

## Stack (all free, no credit card)

| Layer        | Choice                                             |
|--------------|----------------------------------------------------|
| Graph DB     | Neo4j 5 Community (Docker)                          |
| LLM          | Ollama — `qwen2.5:3b-instruct` (light for 16 GB)   |
| Embeddings   | Ollama — `nomic-embed-text`                        |
| Retrieval    | Hybrid (embedding + keyword) → 1–4 hop traversal   |
| UI           | Streamlit + pyvis                                  |

**Key design choice for 16 GB machines:** the graph is loaded **deterministically**
from Python data (no LLM entity extraction). The LLM is used *only at query time*.

## Prerequisites

- Docker Desktop running
- [Ollama](https://ollama.com) running (`ollama serve`)
- [uv](https://docs.astral.sh/uv/) (fast Python env manager)

## Quick start

```bash
# 1. Pull the local models (a few hundred MB + ~2 GB)
ollama pull nomic-embed-text
ollama pull qwen2.5:3b-instruct

# 2. Start Neo4j
docker compose up -d

# 3. Set up the Python environment
cp .env.example .env
uv sync

# 4. Load the supply-chain graph + build embeddings
uv run python -m src.loader
uv run python -m src.embeddings

# 5. Launch the app
uv run streamlit run app/streamlit_app.py
```

Neo4j Browser: http://localhost:7474 (user `neo4j`, password `supplychain`).

## Demo walkthrough

1. **Ask** — type any supply-chain question; Graph RAG answers with cited triples.
2. **Graph vs Vector** — side-by-side: Graph RAG traces dependencies, Vector RAG guesses.
3. **Impact Path** — pick a risk event, see the visual path to affected customers (pyvis).
4. **Explore** — hybrid search over all nodes.
5. **Stats** — node/relationship counts at a glance.

### Run the evaluation suite

```bash
uv run python -m src.eval
```

Runs all 6 ground-truth questions from `data/eval/qa_pairs.yaml` through both
Graph RAG and Vector RAG, printing answers side by side against expected answers.

## Hybrid ingestion — add your own PDFs (optional)

The deterministic seed graph is always the reliable base. You can additionally
extract supply-chain relationships from a PDF and merge them into the *same*
graph using LlamaIndex + the local Ollama model — no new models required.

- In the app, open the **📄 Ingest PDF** page, upload a PDF, click **Extract**,
  review the extracted relationships, then **Add to graph**.
- Everything added is tagged `source='pdf'`; use **Remove all PDF data** to
  restore the pure seed graph.
- Guardrails (configurable in `.env`): `PDF_MAX_MB=5`, `PDF_MAX_CHUNKS=20`,
  `PDF_MAX_NODES=30`. Extraction uses `EXTRACT_MODEL` (defaults to `LLM_MODEL`;
  set it to `llama3.1:8b` for higher-quality extraction).

CLI test:

```bash
uv run python -m src.pdf_ingest data/samples/supply_chain_brief.pdf
```

## Project layout

```
config/         settings loaded from .env
data/           deterministic chip/automotive graph + eval Q&A + sample PDF
src/db.py       Neo4j connection wrapper
src/schema.py   shared entity/relationship schema (seed + PDF)
src/loader.py   load graph (deterministic, no LLM)
src/llm.py      Ollama LLM + embedding helpers
src/embeddings.py  build/store node embeddings, hybrid search
src/graphrag.py    hybrid retrieval → subgraph traversal → grounded answer
src/impact_path.py impact-path Cypher traversal
src/vector_baseline.py  plain vector RAG for comparison
src/pdf_ingest.py  PDF → schema-constrained triples (LlamaIndex + Ollama)
src/graph_writer.py  merge PDF triples into Neo4j (tagged), reset helper
src/eval.py     evaluation runner against ground-truth Q&A
app/            Streamlit UI
```

## License

Original code for this POC. Neo4j Community, Ollama, and the models are used under
their respective open-source licenses.
