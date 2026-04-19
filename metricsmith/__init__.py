"""metricsmith: a small semantic metrics layer that compiles to SQL.

Define metrics and dimensions once in YAML, then ask for them by name. The
compiler turns a query into a single GROUP BY statement with the right joins,
and the runtime executes it so you can prove the numbers.
"""

from .errors import JoinError, MetricsmithError, ModelError, QueryError
from .model import (
    DimensionSpec,
    JoinSpec,
    MetricSpec,
    ModelSpec,
    SemanticLayer,
)
from .query import Query
from .compiler import CompiledQuery, Compiler
from .runtime import QueryResult, Runtime, run_query
from .seed import demo_connection, load_csv_tables

__version__ = "0.2.0"

__all__ = [
    "MetricsmithError",
    "ModelError",
    "QueryError",
    "JoinError",
    "SemanticLayer",
    "ModelSpec",
    "MetricSpec",
    "DimensionSpec",
    "JoinSpec",
    "Query",
    "Compiler",
    "CompiledQuery",
    "Runtime",
    "QueryResult",
    "run_query",
    "demo_connection",
    "load_csv_tables",
    "__version__",
]
