"""Exception hierarchy for metricsmith.

Everything user-facing inherits from MetricsmithError so a CLI or a calling
program can catch one type and show a clean message instead of a traceback.
"""


class MetricsmithError(Exception):
    """Base class for every error metricsmith raises on purpose."""


class ModelError(MetricsmithError):
    """The semantic layer (a model file) is malformed or inconsistent."""


class QueryError(MetricsmithError):
    """A query asked for something the semantic layer can't answer."""


class JoinError(MetricsmithError):
    """Two models can't be connected by any declared join path."""
