"""Thin Neo4j driver wrapper with auto-close."""

from __future__ import annotations

from neo4j import GraphDatabase

from config.settings import settings


class Neo4jConnection:
    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def write(self, cypher: str, params: dict | None = None) -> None:
        with self._driver.session() as session:
            session.run(cypher, params or {})

    def __enter__(self) -> "Neo4jConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
