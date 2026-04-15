"""The semantic layer: models, dimensions, metrics and joins.

A model maps to one physical table. It declares the dimensions you can group
by, the metrics you can aggregate, and the joins that connect it to other
models. A SemanticLayer is a set of models plus the indexes that let a query
resolve a metric or dimension by name.

YAML is validated with pydantic and `extra=forbid`, so a typo in a key is an
error you see at load time rather than a rule that silently never runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pydantic
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._time import GRAINS
from .errors import ModelError

METRIC_TYPES = ("count", "count_distinct", "sum", "average", "min", "max")
DIMENSION_TYPES = ("categorical", "time", "boolean", "numeric")
JOIN_TYPES = ("many_to_one", "one_to_many", "one_to_one")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class JoinSpec(_Base):
    to: str
    sql: str
    type: str = "many_to_one"

    @model_validator(mode="after")
    def _check(self) -> "JoinSpec":
        if self.type not in JOIN_TYPES:
            raise ValueError(f"join type must be one of {', '.join(JOIN_TYPES)}")
        return self


class DimensionSpec(_Base):
    name: str
    sql: Optional[str] = None
    type: str = "categorical"
    description: str = ""

    @model_validator(mode="after")
    def _check(self) -> "DimensionSpec":
        if self.type not in DIMENSION_TYPES:
            raise ValueError(
                f"dimension type must be one of {', '.join(DIMENSION_TYPES)}"
            )
        return self

    def expr(self) -> str:
        return self.sql if self.sql else self.name


class MetricSpec(_Base):
    name: str
    type: str
    sql: Optional[str] = None
    filters: List[str] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _check(self) -> "MetricSpec":
        if self.type not in METRIC_TYPES:
            raise ValueError(f"metric type must be one of {', '.join(METRIC_TYPES)}")
        if self.type != "count" and not self.sql:
            raise ValueError(
                f"metric '{self.name}' of type {self.type} needs a sql expression"
            )
        return self


class ModelSpec(_Base):
    name: str
    table: str
    primary_key: Optional[str] = None
    description: str = ""
    joins: List[JoinSpec] = Field(default_factory=list)
    dimensions: List[DimensionSpec] = Field(default_factory=list)
    metrics: List[MetricSpec] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelSpec":
        try:
            return cls.model_validate(data)
        except pydantic.ValidationError as exc:
            raise ModelError(str(exc)) from exc

    @classmethod
    def from_yaml(cls, path: str) -> "ModelSpec":
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_dict(yaml.safe_load(text))

    def dimension(self, name: str) -> Optional[DimensionSpec]:
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def metric(self, name: str) -> Optional[MetricSpec]:
        for met in self.metrics:
            if met.name == name:
                return met
        return None


class SemanticLayer:
    """A collection of models with name-based lookup for metrics and dims."""

    def __init__(self, models: List[ModelSpec]):
        self.models: Dict[str, ModelSpec] = {}
        self._metric_index: Dict[str, Tuple[ModelSpec, MetricSpec]] = {}
        for spec in models:
            if spec.name in self.models:
                raise ModelError(f"duplicate model '{spec.name}'")
            self.models[spec.name] = spec
        for spec in models:
            for met in spec.metrics:
                if met.name in self._metric_index:
                    other = self._metric_index[met.name][0].name
                    raise ModelError(
                        f"metric '{met.name}' is defined on both '{other}' and "
                        f"'{spec.name}'; metric names must be unique"
                    )
                self._metric_index[met.name] = (spec, met)
        self._validate_joins()

    def _validate_joins(self) -> None:
        for spec in self.models.values():
            for join in spec.joins:
                if join.to not in self.models:
                    raise ModelError(
                        f"model '{spec.name}' joins to unknown model '{join.to}'"
                    )

    @classmethod
    def from_models(cls, models: List[ModelSpec]) -> "SemanticLayer":
        return cls(models)

    @classmethod
    def from_dir(cls, directory: str) -> "SemanticLayer":
        root = Path(directory)
        paths = sorted(p for p in root.glob("*.yml")) + sorted(root.glob("*.yaml"))
        if not paths:
            raise ModelError(f"no model files (*.yml) found in {directory}")
        return cls([ModelSpec.from_yaml(str(p)) for p in paths])

    def metric(self, ref: str) -> Tuple[ModelSpec, MetricSpec]:
        if "." in ref:
            model_name, met_name = ref.split(".", 1)
            model = self.models.get(model_name)
            if model is None:
                raise ModelError(f"unknown model '{model_name}' in metric '{ref}'")
            met = model.metric(met_name)
            if met is None:
                raise ModelError(f"model '{model_name}' has no metric '{met_name}'")
            return model, met
        if ref not in self._metric_index:
            raise ModelError(f"unknown metric '{ref}'")
        return self._metric_index[ref]

    def dimension(self, ref: str) -> Tuple[ModelSpec, DimensionSpec, Optional[str]]:
        grain: Optional[str] = None
        base = ref
        if "__" in ref:
            base, grain = ref.rsplit("__", 1)
        if "." in base:
            model_name, dim_name = base.split(".", 1)
            model = self.models.get(model_name)
            if model is None:
                raise ModelError(f"unknown model '{model_name}' in dimension '{ref}'")
            dim = model.dimension(dim_name)
            if dim is None:
                raise ModelError(
                    f"model '{model_name}' has no dimension '{dim_name}'"
                )
        else:
            matches = [
                (m, d)
                for m in self.models.values()
                for d in m.dimensions
                if d.name == base
            ]
            if not matches:
                raise ModelError(f"unknown dimension '{base}'")
            if len(matches) > 1:
                owners = ", ".join(m.name for m, _ in matches)
                raise ModelError(
                    f"dimension '{base}' is ambiguous (defined on {owners}); "
                    f"qualify it as model.dimension"
                )
            model, dim = matches[0]
        if grain is not None:
            if dim.type != "time":
                raise ModelError(
                    f"grain '{grain}' requested on non-time dimension '{dim.name}'"
                )
            if grain not in GRAINS:
                raise ModelError(
                    f"unknown grain '{grain}', expected one of {', '.join(GRAINS)}"
                )
        return model, dim, grain

    def all_metrics(self) -> List[Tuple[str, MetricSpec]]:
        out = []
        for spec in self.models.values():
            for met in spec.metrics:
                out.append((spec.name, met))
        return out

    def all_dimensions(self) -> List[Tuple[str, DimensionSpec]]:
        out = []
        for spec in self.models.values():
            for dim in spec.dimensions:
                out.append((spec.name, dim))
        return out
