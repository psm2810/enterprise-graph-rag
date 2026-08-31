"""Write PDF-extracted triples into the existing Neo4j graph.

All PDF-derived nodes and relationships are tagged `source='pdf'` (plus a
`document` name) so they can be inspected and removed without touching the
deterministic seed graph. Entities are MERGEd by (label, name): if a PDF
mentions an existing seed entity (e.g. "Acme Corp"), the new facts attach to
that node — demonstrating enrichment — without overwriting its `source`.
"""

from __future__ import annotations

from src.db import Neo4jConnection
from src.embeddings import build_embeddings
from src.schema import ENTITY_TYPES, RELATION_TYPES


def _entity_key(name: str, label: str) -> tuple[str, str]:
    return (label, name)


def _apply_node_cap(triples: list[dict], max_nodes: int) -> tuple[list[dict], bool]:
    """Limit the number of distinct entities introduced by this document.

    Keeps triples in order while the set of referenced entities stays within
    *max_nodes*. Returns (possibly trimmed triples, was_capped).
    """
    allowed: set[tuple[str, str]] = set()
    kept: list[dict] = []
    capped = False
    for t in triples:
        subj_key = _entity_key(t["subject"], t["subject_type"])
        obj_key = _entity_key(t["object"], t["object_type"])
        new_keys = {subj_key, obj_key} - allowed
        if len(allowed) + len(new_keys) > max_nodes:
            capped = True
            continue
        allowed.update(new_keys)
        kept.append(t)
    return kept, capped


def write_triples(triples: list[dict], document: str, max_nodes: int) -> dict:
    """MERGE triples into Neo4j (tagged source='pdf'), then embed new nodes.

    Returns a summary dict with counts.
    """
    triples, capped = _apply_node_cap(triples, max_nodes)

    with Neo4jConnection() as conn:
        before = conn.query(
            "MATCH (n) WHERE n.source = 'pdf' RETURN count(n) AS nodes "
            "UNION ALL "
            "MATCH ()-[r]->() WHERE r.source = 'pdf' RETURN count(r) AS nodes"
        )
        nodes_before, rels_before = before[0]["nodes"], before[1]["nodes"]

        for t in triples:
            subj_label = t["subject_type"]
            obj_label = t["object_type"]
            rel = t["relation"]
            # Guard against injection: labels/relation come only from our schema.
            if subj_label not in ENTITY_TYPES or obj_label not in ENTITY_TYPES:
                continue
            if rel not in RELATION_TYPES:
                continue
            conn.write(
                f"MERGE (a:{subj_label} {{name: $subj}}) "
                f"  ON CREATE SET a.source = 'pdf', a.document = $doc, a.description = '' "
                f"MERGE (b:{obj_label} {{name: $obj}}) "
                f"  ON CREATE SET b.source = 'pdf', b.document = $doc, b.description = '' "
                f"MERGE (a)-[r:{rel}]->(b) "
                f"  ON CREATE SET r.source = 'pdf', r.document = $doc",
                {"subj": t["subject"], "obj": t["object"], "doc": document},
            )

        after = conn.query(
            "MATCH (n) WHERE n.source = 'pdf' RETURN count(n) AS nodes "
            "UNION ALL "
            "MATCH ()-[r]->() WHERE r.source = 'pdf' RETURN count(r) AS nodes"
        )
        nodes_after, rels_after = after[0]["nodes"], after[1]["nodes"]

    # Embed only the newly-added nodes (incremental).
    embedded = build_embeddings(only_missing=True)

    return {
        "triples_written": len(triples),
        "capped": capped,
        "nodes_created": nodes_after - nodes_before,
        "relationships_created": rels_after - rels_before,
        "pdf_nodes_total": nodes_after,
        "pdf_relationships_total": rels_after,
        "nodes_embedded": embedded,
    }


def reset_pdf_data() -> dict:
    """Remove all PDF-derived data, restoring the pure seed graph."""
    with Neo4jConnection() as conn:
        conn.write("MATCH ()-[r]->() WHERE r.source = 'pdf' DELETE r")
        conn.write("MATCH (n) WHERE n.source = 'pdf' DETACH DELETE n")
        totals = conn.query(
            "MATCH (n) RETURN count(n) AS nodes "
            "UNION ALL "
            "MATCH ()-[r]->() RETURN count(r) AS nodes"
        )
    return {"nodes_total": totals[0]["nodes"], "relationships_total": totals[1]["nodes"]}
