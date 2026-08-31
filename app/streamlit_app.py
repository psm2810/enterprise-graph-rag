"""Streamlit UI for Enterprise Graph RAG — Supply-Chain Risk POC."""

from __future__ import annotations

import json

import streamlit as st
from pyvis.network import Network

from config.settings import settings
from src.db import Neo4jConnection
from src.embeddings import hybrid_search
from src.graph_writer import reset_pdf_data, write_triples
from src.graphrag import answer as graph_answer
from src.impact_path import find_impact_paths, paths_to_text
from src.pdf_ingest import PdfTooLargeError, extract_triples
from src.vector_baseline import answer_vector_only

st.set_page_config(page_title="Graph RAG – Supply Chain", layout="wide")

# ── sidebar ──────────────────────────────────────────────────────────────

page = st.sidebar.radio(
    "Navigate",
    ["💬 Ask", "⚔️ Graph vs Vector", "🗺️ Impact Path", "🔍 Explore", "📄 Ingest PDF", "📊 Stats"],
)

# ── helpers ──────────────────────────────────────────────────────────────


def _render_pyvis(paths: list[list[dict]], height: str = "500px") -> None:
    """Render impact paths as a pyvis network embedded in Streamlit."""
    net = Network(height=height, width="100%", directed=True, notebook=False)
    net.barnes_hut()
    added_nodes: set[str] = set()
    color_map = {
        "RiskEvent": "#e74c3c",
        "Factory": "#3498db",
        "Supplier": "#2ecc71",
        "Component": "#f39c12",
        "Product": "#9b59b6",
        "Customer": "#1abc9c",
        "Region": "#95a5a6",
    }
    for chain in paths:
        nodes_in_chain = [s for s in chain if "label" in s]
        rels_in_chain = [s for s in chain if "rel" in s]
        for n in nodes_in_chain:
            nid = n["name"]
            if nid not in added_nodes:
                net.add_node(
                    nid,
                    label=n["name"],
                    color=color_map.get(n["label"], "#bdc3c7"),
                    title=n["label"],
                )
                added_nodes.add(nid)
        for i, rel in enumerate(rels_in_chain):
            if i < len(nodes_in_chain) - 1:
                net.add_edge(nodes_in_chain[i]["name"], nodes_in_chain[i + 1]["name"], label=rel["rel"])

    html = net.generate_html()
    st.components.v1.html(html, height=int(height.replace("px", "")) + 20, scrolling=True)


def _show_seeds(seeds: list[dict]) -> None:
    st.caption("Seed nodes (hybrid search)")
    st.dataframe(seeds, use_container_width=True)


# ── pages ────────────────────────────────────────────────────────────────

if page == "💬 Ask":
    st.header("💬 Ask a Supply-Chain Question")
    question = st.text_input(
        "Question",
        value="How does the chip shortage at Factory A impact Acme Corp?",
    )
    if st.button("Ask (Graph RAG)"):
        with st.spinner("Thinking …"):
            result = graph_answer(question)
        st.subheader("Answer")
        st.write(result["answer"])
        with st.expander(f"📐 {result['triple_count']} graph triples used"):
            st.code("\n".join(result["triples"]))
        _show_seeds(result["seeds"])

elif page == "⚔️ Graph vs Vector":
    st.header("⚔️ Graph RAG vs Plain Vector RAG")
    question = st.text_input(
        "Question",
        value="How does the chip shortage at Factory A impact Acme Corp?",
    )
    if st.button("Compare"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔗 Graph RAG")
            with st.spinner("Graph RAG …"):
                g = graph_answer(question)
            st.write(g["answer"])
            with st.expander(f"{g['triple_count']} triples"):
                st.code("\n".join(g["triples"]))
            _show_seeds(g["seeds"])
        with col2:
            st.subheader("📄 Vector Only")
            with st.spinner("Vector RAG …"):
                v = answer_vector_only(question)
            st.write(v["answer"])
            st.caption(f"Retrieved {v['snippet_count']} snippets")
            _show_seeds(v["seeds"])

elif page == "🗺️ Impact Path":
    st.header("🗺️ Impact-Path Visualisation")
    risk = st.selectbox(
        "Risk Event",
        [
            "Chip Shortage at Factory A",
            "Earthquake in East Asia",
            "Rare-Earth Export Ban",
            "Shipping Lane Disruption",
            "Cybersecurity Breach at Supplier",
        ],
    )
    customer = st.text_input("Filter to customer (optional)")
    if st.button("Trace Impact"):
        with st.spinner("Traversing graph …"):
            paths = find_impact_paths(risk, customer_name=customer or None)
        if paths:
            st.success(f"Found {len(paths)} path(s)")
            _render_pyvis(paths)
            with st.expander("Path details"):
                st.code(paths_to_text(paths))
        else:
            st.warning("No impact paths found.")

elif page == "🔍 Explore":
    st.header("🔍 Explore the Knowledge Graph")
    query = st.text_input("Search nodes", "")
    if query:
        seeds = hybrid_search(query, top_k=10)
        st.dataframe(seeds, use_container_width=True)
    else:
        st.info("Type a search query to find relevant nodes.")

elif page == "📄 Ingest PDF":
    st.header("📄 Ingest a PDF into the Graph")
    st.caption(
        f"Extract supply-chain relationships from a document and merge them into the "
        f"graph. Limits: ≤ {settings.pdf_max_mb:.0f} MB, first {settings.pdf_max_chunks} "
        f"chunks, up to {settings.pdf_max_nodes} new nodes. All added data is tagged "
        f"`source='pdf'` and can be removed below."
    )

    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])

    if uploaded is not None:
        size_mb = uploaded.size / (1024 * 1024)
        if size_mb > settings.pdf_max_mb:
            st.error(f"File is {size_mb:.1f} MB — exceeds the {settings.pdf_max_mb:.0f} MB limit.")
        else:
            st.info(f"`{uploaded.name}` — {size_mb:.2f} MB")
            if st.button("① Extract relationships"):
                with st.spinner("Reading and extracting (this calls the local LLM per chunk) …"):
                    try:
                        triples = extract_triples(uploaded.getvalue())
                        st.session_state["pdf_triples"] = triples
                        st.session_state["pdf_name"] = uploaded.name
                    except PdfTooLargeError as exc:
                        st.error(str(exc))

    triples = st.session_state.get("pdf_triples")
    if triples is not None:
        if triples:
            st.subheader(f"Extracted {len(triples)} relationships (preview)")
            st.dataframe(
                [
                    {
                        "subject": t["subject"],
                        "subject_type": t["subject_type"],
                        "relation": t["relation"],
                        "object": t["object"],
                        "object_type": t["object_type"],
                    }
                    for t in triples
                ],
                use_container_width=True,
            )
            if st.button("② Add to graph"):
                with st.spinner("Merging into Neo4j and embedding new nodes …"):
                    summary = write_triples(
                        triples,
                        document=st.session_state.get("pdf_name", "uploaded.pdf"),
                        max_nodes=settings.pdf_max_nodes,
                    )
                st.success(
                    f"Added {summary['nodes_created']} new nodes and "
                    f"{summary['relationships_created']} new relationships."
                )
                if summary["capped"]:
                    st.warning(
                        f"Node cap ({settings.pdf_max_nodes}) reached — some relationships were skipped."
                    )
                st.session_state.pop("pdf_triples", None)
        else:
            st.warning("No schema-valid relationships were found in this document.")

    st.divider()
    st.subheader("Reset")
    if st.button("🗑️ Remove all PDF data"):
        result = reset_pdf_data()
        st.success(
            f"Removed PDF data. Graph now has {result['nodes_total']} nodes and "
            f"{result['relationships_total']} relationships."
        )

elif page == "📊 Stats":
    st.header("📊 Graph Statistics")
    with Neo4jConnection() as conn:
        node_counts = conn.query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC"
        )
        rel_counts = conn.query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC"
        )
        source_counts = conn.query(
            "MATCH (n) RETURN coalesce(n.source, 'unknown') AS source, count(*) AS count ORDER BY count DESC"
        )
    seed_n = next((r["count"] for r in source_counts if r["source"] == "seed"), 0)
    pdf_n = next((r["count"] for r in source_counts if r["source"] == "pdf"), 0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Seed nodes", seed_n)
    c2.metric("PDF nodes", pdf_n)
    c3.metric("Total nodes", seed_n + pdf_n)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Nodes by label")
        st.dataframe(node_counts, use_container_width=True)
    with col2:
        st.subheader("Relationships by type")
        st.dataframe(rel_counts, use_container_width=True)
