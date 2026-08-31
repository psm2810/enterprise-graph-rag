"""Load the deterministic supply-chain graph into Neo4j.

Usage:
    uv run python -m src.loader          # load (idempotent via MERGE)
    uv run python -m src.loader --clear  # wipe & reload
"""

from __future__ import annotations

import sys

from data.supply_chain_data import (
    COMPONENTS,
    CUSTOMERS,
    FACTORIES,
    PRODUCTS,
    REGIONS,
    RELATIONSHIPS,
    RISK_EVENTS,
    SUPPLIERS,
)
from src.db import Neo4jConnection
from src.schema import ENTITY_TYPES

# ── helpers ──────────────────────────────────────────────────────────────

_DATA_BY_LABEL: dict[str, list[dict]] = {
    "Region": REGIONS,
    "Factory": FACTORIES,
    "Supplier": SUPPLIERS,
    "Component": COMPONENTS,
    "Product": PRODUCTS,
    "Customer": CUSTOMERS,
    "RiskEvent": RISK_EVENTS,
}

# Ordered by the schema so the loader and extractor agree on label set.
_LABEL_DATA: dict[str, list[dict]] = {label: _DATA_BY_LABEL[label] for label in ENTITY_TYPES}


def _create_constraints(conn: Neo4jConnection) -> None:
    for label in ENTITY_TYPES:
        try:
            conn.write(
                f"CREATE CONSTRAINT IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.name IS UNIQUE"
            )
        except Exception:
            pass  # Community edition may not support all constraint syntax


def _merge_nodes(conn: Neo4jConnection) -> int:
    count = 0
    for label, items in _LABEL_DATA.items():
        for item in items:
            set_parts = [f"n.{k} = ${k}" for k in item if k != "name"]
            set_parts.append("n.source = 'seed'")
            cypher = f"MERGE (n:{label} {{name: $name}}) SET {', '.join(set_parts)}"
            conn.write(cypher, item)
            count += 1
    return count


def _merge_relationships(conn: Neo4jConnection) -> int:
    count = 0
    for src_label, src_name, rel_type, tgt_label, tgt_name, props in RELATIONSHIPS:
        params: dict = {"src": src_name, "tgt": tgt_name}
        set_parts = [f"r.{k} = ${k}" for k in props]
        set_parts.append("r.source = 'seed'")
        params.update(props)
        prop_clause = " SET " + ", ".join(set_parts)
        cypher = (
            f"MATCH (a:{src_label} {{name: $src}}), (b:{tgt_label} {{name: $tgt}}) "
            f"MERGE (a)-[r:{rel_type}]->(b){prop_clause}"
        )
        conn.write(cypher, params)
        count += 1
    return count


# ── main ─────────────────────────────────────────────────────────────────

def load_graph(clear: bool = False) -> None:
    with Neo4jConnection() as conn:
        if clear:
            print("Clearing existing graph …")
            conn.write("MATCH (n) DETACH DELETE n")

        print("Creating constraints …")
        _create_constraints(conn)

        print("Loading nodes …")
        n = _merge_nodes(conn)
        print(f"  → {n} nodes merged")

        print("Loading relationships …")
        r = _merge_relationships(conn)
        print(f"  → {r} relationships merged")

        # Quick sanity check
        stats = conn.query(
            "MATCH (n) RETURN count(n) AS nodes "
            "UNION ALL "
            "MATCH ()-[r]->() RETURN count(r) AS nodes"
        )
        print(f"Graph totals: {stats[0]['nodes']} nodes, {stats[1]['nodes']} relationships")
        print("Done ✓")


if __name__ == "__main__":
    load_graph(clear="--clear" in sys.argv)
