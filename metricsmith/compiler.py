"""Compile a Query into SQL.

The compiler is the heart of the project. Given a semantic layer and a query,
it resolves the metrics and dimensions to their owning models, works out which
tables need joining, and assembles a single GROUP BY query. The SQL is built
with sqlglot's expression builder and rendered for the target dialect, so the
output is always parseable rather than string glue.

Metric-level filters become CASE expressions (SUM(CASE WHEN ... THEN x END))
rather than a FILTER clause, because that works on every SQLite build.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from sqlglot import select as sg_select

from . import _time
from .errors import QueryError
from .model import MetricSpec, ModelSpec, SemanticLayer
from .graph import JoinGraph
from .query import Query

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_AGG = {
    "sum": "SUM({0})",
    "average": "AVG({0})",
    "min": "MIN({0})",
    "max": "MAX({0})",
    "count_distinct": "COUNT(DISTINCT {0})",
}


def _qualify(table: str, sql: str) -> str:
    """Prefix a bare column with its table. Leave real expressions alone."""
    stripped = sql.strip()
    if _IDENT.fullmatch(stripped):
        return f"{table}.{stripped}"
    return sql


@dataclass
class CompiledQuery:
    sql: str
    dimensions: List[str]
    metrics: List[str]

    @property
    def columns(self) -> List[str]:
        return self.dimensions + self.metrics


class Compiler:
    def __init__(self, layer: SemanticLayer, dialect: str = "sqlite"):
        self.layer = layer
        self.dialect = dialect
        self.graph = JoinGraph(layer)

    def compile(self, query: Query) -> CompiledQuery:
        metric_specs = [self.layer.metric(m) for m in query.metrics]
        dim_refs = [self.layer.dimension(d) for d in query.dimensions]

        needed: List[str] = []
        for model, _ in metric_specs:
            needed.append(model.name)
        for model, _, _ in dim_refs:
            needed.append(model.name)
        needed = list(dict.fromkeys(needed))

        base, joins = self.graph.connect(needed)
        base_model = self.layer.models[base]

        select_exprs: List[str] = []
        group_exprs: List[str] = []
        dim_aliases: List[str] = []
        used: set = set()
        for model, dim, grain in dim_refs:
            column = _qualify(model.table, dim.expr())
            if grain:
                column_sql = _time.truncate(column, grain, self.dialect)
                alias = f"{dim.name}_{grain}"
            else:
                column_sql = column
                alias = dim.name
            if alias in used:
                alias = f"{model.name}_{alias}"
            used.add(alias)
            select_exprs.append(f"{column_sql} AS {alias}")
            group_exprs.append(column_sql)
            dim_aliases.append(alias)

        metric_aliases: List[str] = []
        for model, metric in metric_specs:
            select_exprs.append(f"{self._metric_sql(model, metric)} AS {metric.name}")
            metric_aliases.append(metric.name)

        statement = sg_select(*select_exprs).from_(base_model.table)
        for edge in joins:
            statement = statement.join(
                edge.table, on=edge.condition, join_type="left"
            )
        for clause in query.filters:
            statement = statement.where(clause)
        if group_exprs:
            statement = statement.group_by(*group_exprs)

        valid = set(dim_aliases) | set(metric_aliases)
        order_terms: List[str] = []
        for term in query.order_by:
            descending = term.startswith("-")
            name = term[1:] if descending else term
            if name not in valid:
                raise QueryError(
                    f"cannot order by '{name}': not a selected metric or dimension"
                )
            order_terms.append(f"{name} DESC" if descending else f"{name} ASC")
        if order_terms:
            statement = statement.order_by(*order_terms)
        if query.limit is not None:
            statement = statement.limit(query.limit)

        sql = statement.sql(dialect=self.dialect, pretty=True)
        return CompiledQuery(sql=sql, dimensions=dim_aliases, metrics=metric_aliases)

    def _metric_sql(self, model: ModelSpec, metric: MetricSpec) -> str:
        condition = ""
        if metric.filters:
            condition = " AND ".join(f"({c})" for c in metric.filters)
        if metric.type == "count":
            if condition:
                return f"COUNT(CASE WHEN {condition} THEN 1 END)"
            return "COUNT(*)"
        column = _qualify(model.table, metric.sql)
        if condition:
            column = f"CASE WHEN {condition} THEN {column} END"
        return _AGG[metric.type].format(column)
