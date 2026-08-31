# Enterprise Graph RAG — Complete Technical Deep Dive

> **Purpose of this document:** A comprehensive, interview-ready explanation of
> every single thing in this project — from scratch. Written so someone who has
> never seen the code can understand what was built, why, and how every piece works.

---

## Table of Contents

1. [The Problem We're Solving](#1-the-problem-were-solving)
2. [What is RAG?](#2-what-is-rag)
3. [What is Vector RAG and Why It Fails Here](#3-what-is-vector-rag-and-why-it-fails-here)
4. [What is Graph RAG and Why It Wins](#4-what-is-graph-rag-and-why-it-wins)
5. [Our Flagship Use Case (The Chip Story)](#5-our-flagship-use-case-the-chip-story)
6. [Technology Stack — What We Installed and Why](#6-technology-stack--what-we-installed-and-why)
7. [Project Structure — Every File Explained](#7-project-structure--every-file-explained)
8. [Step-by-Step: How We Built This](#8-step-by-step-how-we-built-this)
9. [The Data — Where It Comes From](#9-the-data--where-it-comes-from)
10. [The Knowledge Graph Schema](#10-the-knowledge-graph-schema)
11. [How We Load Data Into Neo4j](#11-how-we-load-data-into-neo4j)
12. [Embeddings — What, Why, and How](#12-embeddings--what-why-and-how)
13. [Hybrid Search — Finding the Starting Points](#13-hybrid-search--finding-the-starting-points)
14. [Why Seed Nodes Are the Same for Both Pipelines](#14-why-seed-nodes-are-the-same-for-both-pipelines)
15. [The Graph RAG Pipeline — Step by Step](#15-the-graph-rag-pipeline--step-by-step)
16. [The Vector RAG Pipeline — Step by Step](#16-the-vector-rag-pipeline--step-by-step)
17. [Why Graph RAG Beats Vector RAG — The Real Explanation](#17-why-graph-rag-beats-vector-rag--the-real-explanation)
18. [Impact Path Traversal](#18-impact-path-traversal)
19. [The Streamlit UI — All 5 Pages](#19-the-streamlit-ui--all-5-pages)
20. [Key Design Decisions and Why](#20-key-design-decisions-and-why)
21. [How to Run Everything From Scratch](#21-how-to-run-everything-from-scratch)
22. [Interview Q&A — Questions You Might Be Asked](#22-interview-qa--questions-you-might-be-asked)

---

## 1. The Problem We're Solving

Imagine you work at a large automotive company. You buy chips from semiconductor
factories to build car parts. One day, a factory has a contamination incident and
stops producing chips. Your CEO asks:

> **"How does the chip shortage at Factory A impact our client, Acme Corp?"**

To answer this, a human analyst would need to trace a chain:

1. Factory A produces a specific chip (the NX-7 Microcontroller)
2. That chip goes into a specific product (the DriveECU-500)
3. That product is sold to a specific customer (Acme Corp)

The problem? **No single document, table row, or report contains this full chain.**
The information is spread across different systems:
- The factory database knows Factory A makes NX-7 chips
- The product catalog knows DriveECU-500 uses NX-7 chips
- The sales system knows Acme Corp buys DriveECU-500

A traditional search or AI system that just searches text would have to get lucky
and find all three pieces in the same text snippet. Usually it won't.

**This is the problem Graph RAG solves.** It stores facts as a connected graph and
can *walk the chain* from Factory A all the way to Acme Corp, even though no single
record mentions both.

---

## 2. What is RAG?

**RAG = Retrieval-Augmented Generation.**

It's a pattern for making LLMs (Large Language Models like ChatGPT) smarter by
giving them relevant information before they answer.

Without RAG:
```
User: "How does the chip shortage affect Acme Corp?"
LLM: "I don't have information about your company's supply chain." (or it hallucinates)
```

With RAG:
```
Step 1: RETRIEVE relevant facts from your data
Step 2: Give those facts to the LLM as context
Step 3: LLM GENERATES an answer grounded in those facts
```

The key question is: **how do you retrieve the right facts?** That's where
Vector RAG and Graph RAG differ.

---

## 3. What is Vector RAG and Why It Fails Here

### How Vector RAG works

1. Take every document/record and convert it into a **vector** (a list of numbers,
   e.g., 768 numbers). This is called an **embedding**. Similar texts get similar
   vectors.
2. When a question comes in, convert the question into a vector too.
3. Find the records whose vectors are closest to the question's vector (this is
   called **similarity search** or **nearest-neighbor search**).
4. Give those records to the LLM and ask it to answer.

### Why it fails for multi-hop questions

The question is: *"How does the chip shortage at Factory A impact Acme Corp?"*

Vector search finds the 6 most similar text snippets. Those snippets say things like:
- "Factory A — TSMC advanced 7nm/5nm fab producing automotive and AI chips"
- "Acme Corp — Major North American automaker producing electric trucks and SUVs"
- "Chip Shortage at Factory A — Prolonged wafer contamination incident…"

**But none of these snippets say that Factory A's chip goes into a product that
Acme Corp buys.** That connection lives in the *relationships* between records,
not in any single record's text.

So the LLM gets these snippets and has to **guess**: "Well, Factory A makes chips,
and Acme Corp makes cars, so... maybe they're connected?" It hedges with words
like "likely", "could", "potentially", "if their chips are sourced from…"

**It doesn't actually know. It's speculating.**

---

## 4. What is Graph RAG and Why It Wins

### How Graph RAG works

1. Store your data as a **knowledge graph** — nodes (entities) connected by
   **edges** (relationships).
2. When a question comes in, find the most relevant nodes (same as vector search).
3. **Then do something vector RAG cannot:** walk the edges of the graph outward
   from those nodes. Collect all the connected facts (called **triples**).
4. Give those triples to the LLM. Now it has the full chain.

### What's a triple?

A triple is a fact in the form: **Subject → Relationship → Object**

Examples:
```
Factory "Factory A"  -[PRODUCES]->  Component "NX-7 Microcontroller"
Component "NX-7 Microcontroller"  -[USED_IN]->  Product "DriveECU-500"
Product "DriveECU-500"  -[SOLD_TO]->  Customer "Acme Corp"
```

When the LLM sees these three triples together, it can **provably** trace the chain.
It doesn't guess — it cites the exact path.

---

## 5. Our Flagship Use Case (The Chip Story)

We built a realistic chip/automotive supply-chain scenario. Here's the story:

```
                    THE FLAGSHIP CHAIN
                    ==================

  RiskEvent "Chip Shortage at Factory A"
       │
       │ AFFECTS
       ▼
  Factory "Factory A" (TSMC Fab 18, Tainan, Taiwan)
       │
       │ PRODUCES
       ▼
  Component "NX-7 Microcontroller" (32-bit automotive MCU)
       │
       │ USED_IN
       ▼
  Product "DriveECU-500" (Central powertrain ECU)
       │
       │ SOLD_TO
       ▼
  Customer "Acme Corp" (North American automaker)
```

This is a **4-hop chain**. The risk event is 4 edges away from the customer.
No single record mentions both "Chip Shortage" and "Acme Corp". The graph
connects them through intermediate entities.

**This is why graph beats vector.** Vector RAG would need a single document
that mentions both the chip shortage and Acme Corp to connect them. That
document doesn't exist. The graph stitches it together structurally.

---

## 6. Technology Stack — What We Installed and Why

### Tools on the machine

| Tool | What it is | Why we need it | How we installed it |
|------|-----------|---------------|-------------------|
| **Python 3.12** | Programming language | All our code is Python | Was available via the system (we pinned to 3.12 via `.python-version`) |
| **uv** | Fast Python package manager | Installs dependencies 10-100x faster than pip, manages virtual environments automatically | Was pre-installed via Homebrew |
| **Docker Desktop** | Runs containers (isolated mini-servers) | Runs Neo4j without installing it on the Mac directly | Was pre-installed, we just started it |
| **Ollama** | Local LLM runner | Runs AI models on your laptop without any cloud API or credit card | Was pre-installed |

### Services we run

| Service | What it is | How it runs |
|---------|-----------|-------------|
| **Neo4j 5 Community** | Graph database — stores nodes and relationships | Docker container (via `docker compose up -d`) |
| **Ollama** | Local AI model server | Background service (`ollama serve`) |

### AI Models (downloaded via Ollama, all free)

| Model | Size | Purpose |
|-------|------|---------|
| **qwen2.5:3b-instruct** | ~1.9 GB | The LLM (brain) that reads triples and writes answers. Only 3 billion parameters — chosen because it fits in 16 GB RAM without making the laptop slow. |
| **nomic-embed-text** | ~274 MB | The embedding model — converts text into vectors (lists of numbers) for similarity search. |

### Python Libraries (installed via `uv sync`)

| Library | Purpose |
|---------|---------|
| **neo4j** | Official Python driver to talk to the Neo4j database |
| **ollama** | Python client for the Ollama API (to call the LLM and embedding model) |
| **numpy** | Math library — we use it for cosine similarity calculations |
| **python-dotenv** | Loads configuration from the `.env` file |
| **pyyaml** | Reads the YAML evaluation file |
| **streamlit** | Web UI framework — creates the demo app with almost no frontend code |
| **pyvis** | Graph visualization library — draws interactive network diagrams |

### Key configuration (`.env` file)

```
NEO4J_URI=bolt://localhost:7687      # How Python talks to Neo4j
NEO4J_USER=neo4j                     # Neo4j username
NEO4J_PASSWORD=supplychain           # Neo4j password
OLLAMA_HOST=http://localhost:11434   # Where Ollama runs
LLM_MODEL=qwen2.5:3b-instruct       # Which LLM to use
EMBED_MODEL=nomic-embed-text         # Which embedding model
TOP_K=6                              # How many seed nodes to retrieve
MAX_HOPS=4                           # How far to traverse in the graph
```

---

## 7. Project Structure — Every File Explained

```
enterprise-graph-rag/
│
├── .env.example          ← Template for configuration (copy to .env)
├── .env                  ← Actual config (not in git — has passwords)
├── .gitignore            ← Files git should ignore
├── .python-version       ← Pins Python to 3.12
├── pyproject.toml        ← Project metadata + dependencies
├── docker-compose.yml    ← Defines the Neo4j container
├── README.md             ← Quick-start guide
├── DEEP_DIVE.md          ← This document
│
├── config/
│   ├── __init__.py       ← Makes config/ a Python package
│   └── settings.py       ← Loads .env into a Settings dataclass
│
├── data/
│   ├── __init__.py
│   ├── supply_chain_data.py  ← THE DATA: all nodes + relationships as Python dicts
│   └── eval/
│       └── qa_pairs.yaml     ← Ground-truth Q&A for testing
│
├── src/
│   ├── __init__.py
│   ├── db.py             ← Neo4j connection wrapper
│   ├── loader.py         ← Loads data into Neo4j (no LLM needed)
│   ├── llm.py            ← Ollama helpers (embed text, chat with LLM)
│   ├── embeddings.py     ← Build embeddings + hybrid search
│   ├── graphrag.py       ← THE CORE: hybrid search → graph traversal → LLM answer
│   ├── impact_path.py    ← Traces risk → customer paths via Cypher
│   ├── vector_baseline.py ← Plain vector RAG for comparison
│   └── eval.py           ← Runs all Q&A pairs through both pipelines
│
└── app/
    ├── __init__.py
    └── streamlit_app.py  ← The web UI (5 pages)
```

---

## 8. Step-by-Step: How We Built This

Here is the exact order of operations, from empty folder to working demo:

### Phase 0: Project Scaffold

1. Created `.python-version` (pins to Python 3.12)
2. Created `pyproject.toml` (lists all dependencies)
3. Created `.gitignore` (keeps secrets and generated files out of git)
4. Created `.env.example` (template for configuration)
5. Created `docker-compose.yml` (defines Neo4j container with memory limits)
6. Created `config/settings.py` (loads config from `.env`)
7. Created `README.md` (quick-start instructions)
8. Ran `cp .env.example .env` (created actual config file)
9. Ran `uv sync` (installed all Python dependencies into a virtual environment)

### Phase 1: Pulled AI Models

```bash
ollama pull nomic-embed-text       # ~274 MB download
ollama pull qwen2.5:3b-instruct   # ~1.9 GB download
```

### Phase 2: Created the Data

Created `data/supply_chain_data.py` — all 51 nodes and 76 relationships as
Python lists of dictionaries. No LLM, no web scraping, no external data source.
We authored realistic data inspired by real chip industry players (TSMC, Samsung,
Infineon, etc.).

Created `data/eval/qa_pairs.yaml` — 6 ground-truth questions with expected answers.

### Phase 3: Started Neo4j and Loaded the Graph

```bash
docker compose up -d                    # Started Neo4j container
uv run python -m src.loader --clear     # Loaded all nodes + relationships
```

### Phase 4: Built Embeddings

```bash
uv run python -m src.embeddings         # Embedded all 51 nodes
```

### Phase 5: Created the Core Pipelines

- `src/graphrag.py` — Graph RAG (hybrid search → subgraph expansion → LLM answer)
- `src/vector_baseline.py` — Vector RAG (hybrid search → text snippets → LLM answer)
- `src/impact_path.py` — Direct Cypher traversal for impact visualization

### Phase 6: Created the Streamlit UI

- `app/streamlit_app.py` — 5-page web app

### Phase 7: Tested end-to-end

Ran the flagship question through both pipelines and verified the graph RAG answer
cites the correct chain while the vector RAG answer guesses.

---

## 9. The Data — Where It Comes From

**We wrote it ourselves.** This is a common and accepted approach for POCs.

There is no public, freely available dataset of chip supply-chain relationships
(that data is proprietary to companies like TSMC, Intel, Samsung). So we authored
a realistic but fictional dataset inspired by real industry structure:

- **Real anchors:** TSMC, Samsung, Infineon, GlobalFoundries, ASE Group, Renesas
  are real companies. Fab 18 in Tainan is a real TSMC facility.
- **Fictional entities:** "Acme Corp", "NX-7 Microcontroller", "DriveECU-500" etc.
  are made up to avoid any proprietary claims.
- **Realistic structure:** The relationships (factory produces component, component
  goes into product, product sold to customer) mirror how real supply chains work.

The data is defined as **Python dictionaries** in `data/supply_chain_data.py`.
There are 7 types of entities:

| Entity Type | Count | Examples |
|------------|-------|---------|
| Region | 8 | East Asia, Europe, North America |
| Factory | 6 | Factory A (TSMC), Factory B (Samsung) |
| Supplier | 8 | Supplier Alpha (silicon wafers), Supplier Beta (rare earths) |
| Component | 10 | NX-7 Microcontroller, VPower-300 IGBT |
| Product | 8 | DriveECU-500, ADAS-Platform X |
| Customer | 6 | Acme Corp, Velocity Motors |
| RiskEvent | 5 | Chip Shortage at Factory A, Earthquake in East Asia |

**Total: 51 nodes, 76 relationships**

---

## 10. The Knowledge Graph Schema

A "schema" is the blueprint of what types of nodes and relationships exist.

### Node types and their properties

Every node has at minimum a `name` and `description`. Some have extras:

| Node Label | Key Properties | Example |
|-----------|---------------|---------|
| Region | name, description | "East Asia" |
| Factory | name, company, site, region, description | "Factory A", company="TSMC" |
| Supplier | name, specialty, region, description | "Supplier Alpha", specialty="Raw silicon wafers" |
| Component | name, category, description | "NX-7 Microcontroller", category="MCU" |
| Product | name, type, description | "DriveECU-500", type="ECU" |
| Customer | name, industry, region, description | "Acme Corp", industry="Automotive OEM" |
| RiskEvent | name, severity, description | "Chip Shortage at Factory A", severity="Critical" |

### Relationship types

| Relationship | From → To | Meaning | Example |
|-------------|-----------|---------|---------|
| PRODUCES | Factory → Component | A factory manufactures this component | Factory A → NX-7 Microcontroller |
| SUPPLIES | Supplier → Component | A supplier provides materials for this component | Supplier Alpha → NX-7 Microcontroller |
| USED_IN | Component → Product | This component is used inside this product | NX-7 Microcontroller → DriveECU-500 |
| SOLD_TO | Product → Customer | This product is sold to this customer | DriveECU-500 → Acme Corp |
| LOCATED_IN | Factory/Supplier/Customer → Region | Where the entity is physically located | Factory A → East Asia |
| HAS_ALTERNATIVE | Component → Supplier | A backup supplier exists for this component | NX-7 Microcontroller → Supplier Eta |
| AFFECTS | RiskEvent → Factory/Component/Region/Supplier | What the risk event disrupts | Chip Shortage → Factory A |

### Why this schema matters

The schema is designed so that **no single relationship spans the full chain**.
You need to follow multiple hops:

```
RiskEvent --AFFECTS--> Factory --PRODUCES--> Component --USED_IN--> Product --SOLD_TO--> Customer
```

This is intentional. It's what makes Graph RAG necessary.

---

## 11. How We Load Data Into Neo4j

### What is Neo4j?

Neo4j is a **graph database**. Unlike a table-based database (like MySQL or
PostgreSQL), it stores data as nodes and relationships natively. This makes
"follow the chain" queries extremely fast.

### What is Cypher?

Cypher is Neo4j's query language (like SQL is to relational databases). Examples:

```cypher
-- Find a node
MATCH (f:Factory {name: "Factory A"}) RETURN f

-- Find what Factory A produces
MATCH (f:Factory {name: "Factory A"})-[:PRODUCES]->(c:Component) RETURN c

-- Follow the full chain (this is why we use a graph DB!)
MATCH (r:RiskEvent {name: "Chip Shortage at Factory A"})-[:AFFECTS]->(f:Factory)
      -[:PRODUCES]->(c:Component)-[:USED_IN]->(p:Product)-[:SOLD_TO]->(cust:Customer)
RETURN r, f, c, p, cust
```

### How `src/loader.py` works

1. **Connects** to Neo4j using credentials from `.env`
2. **Creates constraints** — tells Neo4j that each node's `name` must be unique
   (prevents duplicates)
3. **Merges nodes** — for each entity in our data, runs a `MERGE` statement.
   `MERGE` means "create if it doesn't exist, update if it does" — this makes
   loading **idempotent** (safe to run multiple times).
4. **Merges relationships** — for each relationship tuple, finds the source and
   target nodes and creates the edge between them.

Key Cypher example from the loader:
```cypher
MERGE (n:Factory {name: "Factory A"})
SET n.company = "TSMC", n.site = "Fab 18, Tainan", n.description = "..."
```

```cypher
MATCH (a:Factory {name: "Factory A"}), (b:Component {name: "NX-7 Microcontroller"})
MERGE (a)-[r:PRODUCES]->(b)
SET r.volume = "2M units/quarter"
```

### Why no LLM for data loading?

Many Graph RAG tutorials use an LLM to *extract* entities and relationships from
documents. We deliberately avoided this because:

1. **16 GB RAM constraint** — running an LLM to process documents uses a lot of
   memory. Our laptop can't handle it alongside Neo4j.
2. **Determinism** — LLM extraction is unreliable. It might miss entities, create
   duplicates, or invent wrong relationships. Our data is 100% controlled.
3. **Speed** — loading from Python dicts takes seconds. LLM extraction can take
   minutes to hours.

In a production system, you'd build pipelines to extract entities from real
documents (invoices, BOM files, ERP exports). But for a POC, deterministic
data is the right call.

---

## 12. Embeddings — What, Why, and How

### What is an embedding?

An embedding is a **list of numbers** (a vector) that represents the *meaning*
of a piece of text. The model `nomic-embed-text` converts text into a vector
of 768 numbers.

Example:
```
"Factory A — TSMC advanced 7nm fab"  →  [0.023, -0.156, 0.891, ..., 0.042]
                                         (768 numbers)
```

Texts with similar meaning get similar vectors. So "chip factory in Taiwan" and
"semiconductor fab in Tainan" would have vectors that are close together in
768-dimensional space.

### Why do we need embeddings?

When a user asks a question, we need to find which nodes are most relevant.
We can't just do exact keyword matching ("Factory A" might not appear in the
question). Embeddings let us find **semantically similar** nodes — nodes whose
meaning is close to the question's meaning.

### How `src/embeddings.py` builds them

For each of the 51 nodes in Neo4j:

1. **Compose a text** from the node's properties:
   ```
   "Factory Factory A: TSMC advanced 7nm/5nm fab producing automotive
    and AI chips at its Tainan facility. company=TSMC site=Fab 18, Tainan"
   ```
   This is called the `embedding_text`. It includes the label, name, description,
   and any extra properties.

2. **Send that text to Ollama** (`nomic-embed-text` model), which returns a
   768-dimensional vector.

3. **Store the vector back on the Neo4j node** as a property called `embedding`.
   Also store the `embedding_text` (so we can show it later for debugging).

After this step, every node in Neo4j has an `embedding` property (768 floats)
and an `embedding_text` property (the text that was embedded).

---

## 13. Hybrid Search — Finding the Starting Points

### What is hybrid search?

It's a combination of **two** search strategies:

1. **Semantic search (embedding similarity):** Convert the question to a vector,
   then find nodes whose vectors are most similar. This catches meaning-based
   matches (e.g., "chip shortage" matches "semiconductor fab").

2. **Keyword overlap:** Check how many words from the question appear in the
   node's text. This catches exact matches (e.g., the word "Factory A" literally
   appears in the node's text).

The final score is a weighted combination:

```
score = 0.7 × cosine_similarity + 0.3 × keyword_overlap
```

We weight semantic search higher (0.7) because it's better at understanding
meaning, but keyword overlap (0.3) helps when exact entity names appear in
the question.

### What is cosine similarity?

A way to measure how similar two vectors are. It's the cosine of the angle
between them:

- **1.0** = identical direction (very similar text)
- **0.0** = perpendicular (unrelated)
- **-1.0** = opposite (very different — rare in practice)

Formula:
```
cosine_sim(A, B) = (A · B) / (|A| × |B|)
```

Where `A · B` is the dot product and `|A|` is the vector's length (magnitude).
We use NumPy to compute this efficiently.

### What are "seed nodes"?

**Seed nodes are the top-k results of hybrid search.** They are the starting
points for the next step.

For the question *"How does the chip shortage at Factory A impact Acme Corp?"*,
the top 6 seed nodes might be:

| # | Label | Name | Score |
|---|-------|------|-------|
| 1 | RiskEvent | Chip Shortage at Factory A | 0.7523 |
| 2 | Factory | Factory A | 0.6891 |
| 3 | Customer | Acme Corp | 0.6234 |
| 4 | Component | NX-7 Microcontroller | 0.5812 |
| 5 | Product | DriveECU-500 | 0.5103 |
| 6 | Region | East Asia | 0.4897 |

These seed nodes are where both pipelines (Graph RAG and Vector RAG) start.
What they do *next* is what makes them different.

---

## 14. Why Seed Nodes Are the Same for Both Pipelines

**This is by design and it's important for a fair comparison.**

Both Graph RAG and Vector RAG call the exact same `hybrid_search()` function.
They get the exact same 6 seed nodes with the exact same scores.

Think of it like two detectives given the same list of suspects:

- **Detective Graph (Graph RAG):** Takes the suspects, then goes and
  investigates — follows connections, interviews associates, traces the chain.
  Returns with proof: "Suspect A sold guns to Suspect B who gave them to
  Suspect C."

- **Detective Vector (Vector RAG):** Takes the suspects, reads their public
  bios, and writes a report based on that. "Suspect A might be connected to
  Suspect C because they're both in the same city."

**Same starting clues. Completely different depth of investigation.**

The seeds being identical actually *strengthens* the demo — it proves that
the difference isn't about finding better starting points. It's about
**what you do after finding them.**

---

## 15. The Graph RAG Pipeline — Step by Step

File: `src/graphrag.py`

When you ask: *"How does the chip shortage at Factory A impact Acme Corp?"*

### Step 1: Hybrid Search (find seed nodes)

```python
seeds = hybrid_search(question, top_k=6)
# Result: ["Chip Shortage at Factory A", "Factory A", "Acme Corp",
#          "NX-7 Microcontroller", "DriveECU-500", "East Asia"]
```

### Step 2: Subgraph Expansion (traverse the graph)

For each seed node, run a Cypher query that walks up to 4 hops in all
directions and collects every triple (relationship) found:

```cypher
UNWIND $seeds AS seed
MATCH (start {name: seed})
MATCH path = (start)-[*1..4]-(connected)
UNWIND relationships(path) AS r
WITH startNode(r) AS a, type(r) AS rel, endNode(r) AS b
RETURN DISTINCT
  labels(a)[0] + ' "' + a.name + '"' AS src,
  rel,
  labels(b)[0] + ' "' + b.name + '"' AS tgt
```

This returns ~76 triples like:
```
Factory "Factory A" -[PRODUCES]-> Component "NX-7 Microcontroller"
Component "NX-7 Microcontroller" -[USED_IN]-> Product "DriveECU-500"
Product "DriveECU-500" -[SOLD_TO]-> Customer "Acme Corp"
RiskEvent "Chip Shortage at Factory A" -[AFFECTS]-> Factory "Factory A"
... (and 72 more)
```

**This is the key step that vector RAG does not have.** The graph traversal
discovers the complete chain from risk event to customer.

### Step 3: Build the Prompt

Concatenate all triples into a context block and send to the LLM:

```
System: You are a supply-chain risk analyst. Answer the user's question
using ONLY the graph triples provided below. Cite specific entities and
relationships.

User:
### Graph triples (knowledge graph context)
Factory "Factory A" -[PRODUCES]-> Component "NX-7 Microcontroller"
Component "NX-7 Microcontroller" -[USED_IN]-> Product "DriveECU-500"
Product "DriveECU-500" -[SOLD_TO]-> Customer "Acme Corp"
RiskEvent "Chip Shortage at Factory A" -[AFFECTS]-> Factory "Factory A"
... (76 total)

### Question
How does the chip shortage at Factory A impact Acme Corp?
```

### Step 4: LLM Generates a Grounded Answer

The LLM sees the triples and can trace the chain. Its answer cites specific
entities and relationships:

> "The chip shortage at Factory A impacts Acme Corp by affecting the supply
> of the NX-7 Microcontroller, which is used in the DriveECU-500. Since
> the DriveECU-500 is sold to Acme Corp, the shortage directly disrupts
> Acme Corp's supply chain."

**The LLM didn't guess.** It read the triples and followed the chain.

---

## 16. The Vector RAG Pipeline — Step by Step

File: `src/vector_baseline.py`

### Step 1: Hybrid Search (same as Graph RAG)

```python
seeds = hybrid_search(question, top_k=6)
# Same 6 nodes as Graph RAG
```

### Step 2: Fetch Text Snippets (NO graph traversal)

Instead of expanding the subgraph, just retrieve the `embedding_text` of
each seed node:

```python
# Fetches 6 text snippets:
"RiskEvent Chip Shortage at Factory A: Prolonged wafer contamination incident..."
"Factory Factory A: TSMC advanced 7nm/5nm fab producing automotive and AI chips..."
"Customer Acme Corp: Major North American automaker producing electric trucks..."
"Component NX-7 Microcontroller: 32-bit automotive-grade microcontroller..."
"Product DriveECU-500: Central powertrain ECU for electric and hybrid vehicles."
"Region East Asia: Major semiconductor manufacturing hub..."
```

**Notice:** None of these snippets say that Factory A produces NX-7, or
that NX-7 goes into DriveECU-500, or that DriveECU-500 is sold to Acme Corp.
Those facts live in the relationships, which vector RAG doesn't retrieve.

### Step 3: Build the Prompt

```
System: You are a supply-chain analyst. Answer using ONLY the text snippets.

User:
### Retrieved snippets
- RiskEvent Chip Shortage at Factory A: Prolonged wafer contamination incident...
- Factory Factory A: TSMC advanced 7nm/5nm fab producing automotive and AI chips...
- Customer Acme Corp: Major North American automaker producing electric trucks...
- Component NX-7 Microcontroller: 32-bit automotive-grade microcontroller...
- Product DriveECU-500: Central powertrain ECU for electric and hybrid vehicles.
- Region East Asia: Major semiconductor manufacturing hub...

### Question
How does the chip shortage at Factory A impact Acme Corp?
```

### Step 4: LLM Guesses

The LLM sees unrelated descriptions and has to speculate:

> "The chip shortage at Factory A would likely lead to delays... This could
> result in reduced output... specific details about the impact on Acme Corp
> would require additional information not provided in the snippet."

**It literally says "not provided in the snippet."** Because it isn't — the
connection lives in the graph edges, not in the text.

---

## 17. Why Graph RAG Beats Vector RAG — The Real Explanation

Here's a table summarizing every difference:

| Aspect | Graph RAG | Vector RAG |
|--------|-----------|------------|
| **Step 1** | Hybrid search → 6 seed nodes | Hybrid search → 6 seed nodes (SAME) |
| **Step 2** | Traverse graph edges → 76 triples | Fetch text descriptions → 6 snippets |
| **What LLM sees** | Structural facts: "A produces B, B used in C, C sold to D" | Isolated descriptions: "A is a factory", "D is a customer" |
| **Can it trace the chain?** | YES — the triples ARE the chain | NO — the snippets don't connect |
| **Answer quality** | Specific, cites entities and paths | Vague, uses "likely", "could", "potentially" |
| **Provable?** | YES — every claim maps to a triple | NO — LLM is inferring |
| **Works with sparse descriptions?** | YES — relationships carry the info | NO — relies on rich text |

### The analogy

Imagine asking: "How is person X related to person Y?"

- **Graph RAG:** Looks at a family tree. "X is the mother of Z, Z is married to Y.
  Therefore, X is Y's mother-in-law."

- **Vector RAG:** Reads X's LinkedIn bio and Y's LinkedIn bio. "They both work in
  tech and live in California, so they might know each other."

The family tree (graph) has the structural proof. The bios (text) don't.

### Why did the first version look similar?

When we first built the demo, our node descriptions contained "leaky" hints like:
- Acme Corp's description said "relies on the DriveECU-500"
- The risk event description named "the NX-7 Microcontroller"

This meant the vector snippets accidentally contained the chain information in
the text itself. Vector RAG was "cheating" — reading the answers from the text
instead of discovering them from relationships.

We fixed this by making descriptions generic (only describing *what the entity is*,
not *what it connects to*). After this fix, the vector RAG answer clearly shows
its weakness.

---

## 18. Impact Path Traversal

File: `src/impact_path.py`

This is a separate feature that uses direct Cypher queries (no LLM, no embeddings)
to find all paths from a risk event to affected customers.

### The Cypher query

```cypher
MATCH (r:RiskEvent {name: "Chip Shortage at Factory A"})-[:AFFECTS]->(affected)
MATCH path = (affected)-[:PRODUCES|SUPPLIES|USED_IN|SOLD_TO*0..6]->(c:Customer {name: "Acme Corp"})
RETURN path
```

Translation:
1. Find the risk event node
2. Find what it AFFECTS (could be a factory, component, supplier, or region)
3. From each affected node, follow PRODUCES/SUPPLIES/USED_IN/SOLD_TO edges
   up to 6 hops until you reach the customer "Acme Corp"
4. Return all such paths

For our flagship question, this returns 4 paths:
```
Path 1: Component "NX-7 Microcontroller" → Product "DriveECU-500" → Customer "Acme Corp"
Path 2: Component "NX-7 Microcontroller" → Product "ADAS-Platform X" → Customer "Acme Corp"
Path 3: Factory "Factory A" → Component "NX-7" → Product "DriveECU-500" → Customer "Acme Corp"
Path 4: Factory "Factory A" → Component "NX-7" → Product "ADAS-Platform X" → Customer "Acme Corp"
```

These paths are visualized as interactive network graphs in the Streamlit UI
using pyvis.

---

## 19. The Streamlit UI — All 5 Pages

File: `app/streamlit_app.py`

### Page 1: 💬 Ask

A simple Q&A interface. Type a question, get a Graph RAG answer. Below the answer,
you can expand to see the actual triples used and the seed nodes.

### Page 2: ⚔️ Graph vs Vector

Side-by-side comparison. Same question, two columns. Left: Graph RAG answer with
triples. Right: Vector RAG answer with just snippets. This is the "wow" page
for demos.

### Page 3: 🗺️ Impact Path

Choose a risk event from a dropdown (e.g., "Chip Shortage at Factory A"),
optionally filter to a specific customer, and see an interactive graph visualization
of all impact paths. Uses pyvis to render colored nodes (red for risk, blue for
factory, orange for component, purple for product, teal for customer).

### Page 4: 🔍 Explore

Free-form search. Type anything and see the top-10 matching nodes from hybrid
search. Good for exploring the graph.

### Page 5: 📊 Stats

Shows node counts by label and relationship counts by type. Quick overview of
the graph.

---

## 20. Key Design Decisions and Why

### Decision 1: Deterministic data loading (no LLM entity extraction)

**Why:** On a 16 GB laptop, running an LLM to extract entities from documents
would consume too much RAM alongside Neo4j. Also, LLM extraction is unreliable —
it might miss entities or create wrong relationships. Deterministic Python dicts
are 100% controlled and load in seconds.

### Decision 2: 3B parameter model (qwen2.5:3b-instruct)

**Why:** Smaller models use less RAM. The LLM's job is simple — read triples and
compose an answer. It doesn't need to be a genius; the graph did the hard work.
A 3B model fits comfortably in 16 GB alongside Neo4j and the embedding model.

### Decision 3: Embeddings stored on Neo4j nodes (not in a separate vector DB)

**Why:** With only 51 nodes, we don't need a dedicated vector database (like Pinecone,
Weaviate, or FAISS). We store the 768-float vector directly as a node property
and compute cosine similarity in Python. Simpler architecture, fewer moving parts.

### Decision 4: Hybrid search (embedding + keyword)

**Why:** Pure embedding search might rank "semiconductor factory" higher than
"Factory A" for the query "Factory A". Adding keyword overlap ensures exact name
matches get a boost. The 70/30 split favors semantic understanding while still
rewarding literal matches.

### Decision 5: Descriptions don't leak cross-entity information

**Why:** If Acme Corp's description said "relies on DriveECU-500", vector RAG
would find the answer in the text and the demo wouldn't show Graph RAG's advantage.
We made descriptions self-contained (only describing what the entity *is*) so the
relationships in the graph are the only way to discover connections.

### Decision 6: MERGE instead of CREATE for loading

**Why:** `MERGE` in Cypher means "create if not exists, update if exists". This
makes the loader **idempotent** — you can run it multiple times without creating
duplicate nodes. Useful during development and for reloading data.

---

## 21. How to Run Everything From Scratch

If you cloned this repo on a fresh machine with Docker, Ollama, and uv installed:

```bash
# 1. Pull AI models (one-time, ~2.2 GB total)
ollama pull nomic-embed-text
ollama pull qwen2.5:3b-instruct

# 2. Start Neo4j
docker compose up -d

# 3. Install Python dependencies
cp .env.example .env
uv sync

# 4. Load the knowledge graph (51 nodes, 76 relationships)
uv run python -m src.loader --clear

# 5. Build embeddings for all nodes
uv run python -m src.embeddings

# 6. Launch the web UI
uv run streamlit run app/streamlit_app.py

# 7. (Optional) Run evaluation
uv run python -m src.eval
```

The app is at http://localhost:8501.
Neo4j Browser is at http://localhost:7474 (user: neo4j, password: supplychain).

---

## 22. Interview Q&A — Questions You Might Be Asked

### Q: What is Graph RAG?

**A:** Graph RAG is Retrieval-Augmented Generation where the retrieval step uses a
knowledge graph instead of (or in addition to) a vector store. It finds relevant
entities via embeddings, then traverses graph relationships to collect connected
facts (triples), which are given to an LLM as grounded context for answering.

### Q: Why did you use a knowledge graph instead of a regular vector store?

**A:** Our supply-chain data is inherently relational — factories produce components,
components go into products, products are sold to customers. The answer to "how does
a risk at Factory A affect Customer X?" requires tracing 4 hops across relationships.
No single document contains this full chain. A vector store retrieves isolated text
snippets; a graph traverses the actual dependency path.

### Q: What are embeddings?

**A:** Embeddings are fixed-length vectors (lists of numbers) that capture the semantic
meaning of text. Similar texts produce similar vectors. We use them to find which
nodes in the graph are most relevant to a user's question, even if the exact words
don't match.

### Q: What is cosine similarity?

**A:** A measure of how similar two vectors are, computed as the dot product divided
by the product of their magnitudes. It ranges from -1 (opposite) to 1 (identical).
We use it to rank nodes by relevance to the user's question.

### Q: What are seed nodes?

**A:** The top-k nodes returned by hybrid search. They're the starting points for
graph traversal. Both Graph RAG and Vector RAG use the same seed nodes — the
difference is that Graph RAG then expands outward via relationships, while Vector
RAG only reads the text of those same nodes.

### Q: Why are the seed nodes the same for both Graph RAG and Vector RAG?

**A:** Both use the same hybrid search function (same embeddings, same scoring).
This is intentional — it makes the comparison fair. The difference isn't about
finding better starting points; it's about what each pipeline does *after*
finding them. Graph RAG traverses relationships; Vector RAG reads text snippets.

### Q: What is a triple?

**A:** A fact in the form Subject → Relationship → Object. For example:
`Factory "Factory A" -[PRODUCES]-> Component "NX-7 Microcontroller"`.
Triples are the atoms of a knowledge graph. Our graph has 76 triples.

### Q: Why didn't you use an LLM to extract entities from documents?

**A:** Three reasons: (1) 16 GB RAM constraint — LLM extraction during data loading
is memory-intensive alongside Neo4j, (2) deterministic data is more reliable than
LLM extraction which can miss entities or hallucinate relationships, (3) for a
POC, authored data loads in seconds vs. minutes for LLM extraction.

### Q: What is Neo4j?

**A:** A graph database that stores data as nodes (entities) and relationships
(edges) natively. Unlike relational databases that use tables and JOINs, Neo4j
represents connections directly, making multi-hop traversals very fast. We use
its query language, Cypher, to load data and traverse paths.

### Q: What is Ollama?

**A:** A tool that lets you run open-source LLMs locally on your laptop. No cloud
API, no credit card, no data leaving your machine. We use it for two models:
qwen2.5:3b-instruct (for generating answers) and nomic-embed-text (for creating
embeddings).

### Q: What is hybrid search?

**A:** A search strategy combining embedding similarity (70%) and keyword overlap
(30%). Embedding similarity catches semantic matches ("chip disruption" ≈
"semiconductor shortage"). Keyword overlap catches literal matches ("Factory A"
= "Factory A"). The weighted combination gives better results than either alone.

### Q: How does the impact path visualization work?

**A:** It runs a Cypher query that starts from a risk event, follows its AFFECTS
relationships, then traverses PRODUCES/SUPPLIES/USED_IN/SOLD_TO edges up to 6
hops to reach Customer nodes. The resulting paths are rendered as interactive
network graphs using pyvis, with color-coded nodes.

### Q: What would you do differently in production?

**A:** (1) Use a dedicated vector index (Neo4j's built-in or FAISS) instead of
brute-force cosine similarity in Python — our 51-node graph is tiny but a
production graph would have millions of nodes. (2) Add LLM-based entity extraction
from real documents (invoices, BOMs, ERP data) alongside the deterministic load.
(3) Use a larger LLM (7-13B) on a GPU server for better answer quality.
(4) Add authentication, rate limiting, and logging. (5) Implement incremental
graph updates rather than full reload.

### Q: Why Streamlit?

**A:** Streamlit lets you build interactive web UIs in pure Python with almost no
frontend code. Perfect for POCs and demos. It's not meant for production scale,
but for showing the concept to stakeholders it's ideal.

### Q: What is Docker Compose?

**A:** A tool for defining and running multi-container Docker applications. Our
`docker-compose.yml` defines a single service (Neo4j) with its configuration
(ports, memory limits, passwords). Running `docker compose up -d` starts it
in the background. In production, you'd add the API server and Streamlit
as additional services.
