"""Single source of truth for the supply-chain graph schema.

Used by both the deterministic loader (`src/loader.py`) and the PDF
extraction pipeline (`src/pdf_ingest.py`) so that everything written to
Neo4j — whether seeded or extracted from a document — shares the exact
same entity labels and relationship types.
"""

from __future__ import annotations

# ── Entity labels (node types) ───────────────────────────────────────────
ENTITY_TYPES: list[str] = [
    "Region",
    "Factory",
    "Supplier",
    "Component",
    "Product",
    "Customer",
    "RiskEvent",
]

# ── Relationship types ───────────────────────────────────────────────────
RELATION_TYPES: list[str] = [
    "PRODUCES",
    "SUPPLIES",
    "USED_IN",
    "SOLD_TO",
    "LOCATED_IN",
    "HAS_ALTERNATIVE",
    "AFFECTS",
]

# ── Valid triples: (subject_label, relation, object_label) ───────────────
# Constrains extraction so the graph stays coherent and existing traversal
# features (impact path, etc.) keep working on PDF-derived data.
VALID_TRIPLES: set[tuple[str, str, str]] = {
    ("Factory", "PRODUCES", "Component"),
    ("Supplier", "SUPPLIES", "Component"),
    ("Component", "USED_IN", "Product"),
    ("Product", "SOLD_TO", "Customer"),
    ("Factory", "LOCATED_IN", "Region"),
    ("Supplier", "LOCATED_IN", "Region"),
    ("Customer", "LOCATED_IN", "Region"),
    ("Component", "HAS_ALTERNATIVE", "Supplier"),
    ("RiskEvent", "AFFECTS", "Factory"),
    ("RiskEvent", "AFFECTS", "Component"),
    ("RiskEvent", "AFFECTS", "Region"),
    ("RiskEvent", "AFFECTS", "Supplier"),
}


def is_valid_triple(subject_label: str, relation: str, object_label: str) -> bool:
    """Return True if (subject)-[relation]->(object) is allowed by the schema."""
    return (subject_label, relation, object_label) in VALID_TRIPLES
