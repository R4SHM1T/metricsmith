"""The Query object: what a caller asks the semantic layer for.

A query is intentionally dumb. It names metrics and dimensions (by their
semantic names, not SQL), plus optional filters, ordering and a limit. Turning
that into SQL is the compiler's job, not the query's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .errors import QueryError

_ALLOWED_KEYS = {"metrics", "dimensions", "filters", "order_by", "limit"}


@dataclass
class Query:
    """A request for one or more metrics, optionally sliced by dimensions.

    order_by entries name a selected metric or dimension; prefix with '-' for
    descending (for example '-total_revenue').
    """

    metrics: List[str]
    dimensions: List[str] = field(default_factory=list)
    filters: List[str] = field(default_factory=list)
    order_by: List[str] = field(default_factory=list)
    limit: Optional[int] = None

    def __post_init__(self) -> None:
        if isinstance(self.metrics, str):
            self.metrics = [self.metrics]
        if not self.metrics:
            raise QueryError("a query needs at least one metric")
        if self.limit is not None and self.limit < 0:
            raise QueryError("limit cannot be negative")

    @classmethod
    def from_dict(cls, data: dict) -> "Query":
        unknown = set(data) - _ALLOWED_KEYS
        if unknown:
            raise QueryError(f"unknown query field(s): {', '.join(sorted(unknown))}")
        return cls(
            metrics=list(data.get("metrics", [])),
            dimensions=list(data.get("dimensions", [])),
            filters=list(data.get("filters", [])),
            order_by=list(data.get("order_by", [])),
            limit=data.get("limit"),
        )
