"""Impact-path traversal: trace a risk event to affected customers."""

from __future__ import annotations

from src.db import Neo4jConnection


def find_impact_paths(
    risk_name: str,
    customer_name: str | None = None,
    max_hops: int = 6,
) -> list[list[dict]]:
    """Return paths from a RiskEvent to Customer nodes.

    Each path is a list of dicts: [{label, name}, {rel}, {label, name}, …].
    """
    customer_filter = ""
    params: dict = {"risk": risk_name}
    if customer_name:
        customer_filter = " {name: $customer}"
        params["customer"] = customer_name

    cypher = (
        "MATCH (r:RiskEvent {name: $risk})-[:AFFECTS]->(affected) "
        "MATCH path = (affected)-[:PRODUCES|SUPPLIES|USED_IN|SOLD_TO*0.."
        + str(max_hops)
        + "]->(c:Customer"
        + customer_filter
        + ") "
        "UNWIND range(0, size(nodes(path))-1) AS i "
        "WITH path, i, nodes(path)[i] AS n "
        "RETURN [x IN nodes(path) | {label: labels(x)[0], name: x.name}] AS node_list, "
        "       [r2 IN relationships(path) | type(r2)] AS rel_list"
    )

    with Neo4jConnection() as conn:
        raw = conn.query(cypher, params)

    # Deduplicate (the UNWIND produces repeated rows)
    seen: set[str] = set()
    paths: list[list[dict]] = []
    for row in raw:
        nodes = row["node_list"]
        rels = row["rel_list"]
        key = str(nodes) + str(rels)
        if key in seen:
            continue
        seen.add(key)
        chain: list[dict] = []
        for j, n in enumerate(nodes):
            chain.append({"label": n["label"], "name": n["name"]})
            if j < len(rels):
                chain.append({"rel": rels[j]})
        paths.append(chain)
    return paths


def paths_to_text(paths: list[list[dict]]) -> str:
    """Pretty-print paths for display / LLM context."""
    lines: list[str] = []
    for i, chain in enumerate(paths, 1):
        parts: list[str] = []
        for step in chain:
            if "rel" in step:
                parts.append(f"-[{step['rel']}]->")
            else:
                parts.append(f"{step['label']} \"{step['name']}\"")
        lines.append(f"Path {i}: {' '.join(parts)}")
    return "\n".join(lines)
