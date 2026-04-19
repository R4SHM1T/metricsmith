"""Execute compiled queries against a DB-API connection (SQLite by default).

The runtime is deliberately thin: compile, execute, hand back rows as dicts
along with the SQL that produced them. Keeping the SQL on the result makes it
easy to show your work, which is half the point of a metrics layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .compiler import CompiledQuery, Compiler
from .model import SemanticLayer
from .query import Query


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[Dict[str, Any]]
    sql: str

    def __iter__(self):
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)


class Runtime:
    def __init__(self, layer: SemanticLayer, connection, dialect: str = "sqlite"):
        self.layer = layer
        self.connection = connection
        self.compiler = Compiler(layer, dialect=dialect)

    def compile(self, query: Query) -> CompiledQuery:
        return self.compiler.compile(query)

    def run(self, query: Query) -> QueryResult:
        compiled = self.compiler.compile(query)
        cursor = self.connection.execute(compiled.sql)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, record)) for record in cursor.fetchall()]
        return QueryResult(columns=columns, rows=rows, sql=compiled.sql)


def run_query(layer: SemanticLayer, query: Query, connection) -> QueryResult:
    """Convenience wrapper: compile and execute in one call."""
    return Runtime(layer, connection).run(query)
