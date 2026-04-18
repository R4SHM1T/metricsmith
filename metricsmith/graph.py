"""Join resolution.

Models declare joins to their neighbours. When a query touches more than one
model, we need a path that connects them. The graph is treated as undirected:
a join declared on one side can be traversed from either end, since the join
condition is an equality that holds both ways.

The base model becomes the FROM table; everything else is reached by walking
the shortest path and emitting a LEFT JOIN per hop.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .errors import JoinError
from .model import SemanticLayer

_REVERSE = {
    "many_to_one": "one_to_many",
    "one_to_many": "many_to_one",
    "one_to_one": "one_to_one",
}


@dataclass
class JoinEdge:
    model: str
    table: str
    condition: str
    type: str


class JoinGraph:
    def __init__(self, layer: SemanticLayer):
        self.layer = layer
        self.adj: Dict[str, List[Tuple[str, str, str]]] = {
            name: [] for name in layer.models
        }
        for spec in layer.models.values():
            for join in spec.joins:
                self.adj[spec.name].append((join.to, join.sql, join.type))
                self.adj[join.to].append(
                    (spec.name, join.sql, _REVERSE.get(join.type, join.type))
                )

    def _path(self, base: str, target: str) -> Optional[List[Tuple[str, str, str]]]:
        """Breadth-first search from base to target.

        Returns the hops (neighbour, condition, type) in order, or None.
        """
        if base == target:
            return []
        prev: Dict[str, Tuple[str, str, str]] = {}
        seen = {base}
        queue = deque([base])
        while queue:
            node = queue.popleft()
            for neighbour, condition, jtype in self.adj[node]:
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                prev[neighbour] = (node, condition, jtype)
                if neighbour == target:
                    return self._rebuild(prev, base, target)
                queue.append(neighbour)
        return None

    @staticmethod
    def _rebuild(prev, base, target):
        hops = []
        node = target
        while node != base:
            parent, condition, jtype = prev[node]
            hops.append((node, condition, jtype))
            node = parent
        hops.reverse()
        return hops

    def connect(self, models: List[str]) -> Tuple[str, List[JoinEdge]]:
        """Pick a base model and return the joins needed to reach the rest."""
        if not models:
            raise JoinError("no models to connect")
        base = models[0]
        seen = {base}
        edges: List[JoinEdge] = []
        for target in models[1:]:
            if target in seen:
                continue
            path = self._path(base, target)
            if path is None:
                raise JoinError(
                    f"no join path connects '{base}' and '{target}'"
                )
            for neighbour, condition, jtype in path:
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                edges.append(
                    JoinEdge(
                        model=neighbour,
                        table=self.layer.models[neighbour].table,
                        condition=condition,
                        type=jtype,
                    )
                )
        return base, edges
