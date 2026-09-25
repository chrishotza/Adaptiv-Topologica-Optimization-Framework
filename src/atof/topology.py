from __future__ import annotations
import math
import warnings
from dataclasses import dataclass, asdict
from typing import Any, Sequence
import networkx as nx


PROFILE_FEATURES = (
    "node_count",
    "edge_count",
    "density",
    "avg_degree",
    "degree_std",
    "max_degree",
    "hub_ratio",
    "degree_gini",
    "clustering",
    "transitivity",
    "assortativity",
    "core_number",
    "diameter",
    "avg_path_length",
    "communities",
    "modularity",
)

_DEGREE_FEATURES = {
    "avg_degree",
    "degree_std",
    "max_degree",
    "hub_ratio",
    "degree_gini",
}
_COMPONENT_FEATURES = {"diameter", "avg_path_length"}
_COMMUNITY_FEATURES = {"communities", "modularity"}


def resolve_profile_features(
    features: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Validate and normalize the requested profile fields."""
    selected = PROFILE_FEATURES if features is None else tuple(features)
    if not selected:
        raise ValueError("features must contain at least one topology profile feature")
    unknown = sorted(set(selected).difference(PROFILE_FEATURES))
    if unknown:
        raise ValueError(
            "unknown topology profile features: " + ", ".join(unknown)
        )
    if len(set(selected)) != len(selected):
        raise ValueError("features must not contain duplicates")
    return selected


@dataclass(frozen=True)
class TopologyProfile:
    node_count: int
    edge_count: int
    density: float
    avg_degree: float
    degree_std: float
    max_degree: int
    hub_ratio: float
    degree_gini: float
    clustering: float
    transitivity: float
    assortativity: float
    core_number: float
    diameter: float
    avg_path_length: float
    communities: int
    modularity: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TopologyProfiler:
    """Compute interpretable structural descriptors for a graph.

    By default every descriptor is computed, preserving the historical API.
    Pass a feature subset to avoid evaluating expensive descriptors that a
    downstream router does not use.
    """

    def __init__(self, features: Sequence[str] | None = None) -> None:
        self.features = resolve_profile_features(features)

    @staticmethod
    def _gini(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        total = sum(ordered)
        n = len(ordered)
        if total == 0:
            return 0.0
        weighted = sum((i + 1) * value for i, value in enumerate(ordered))
        return (2 * weighted) / (n * total) - (n + 1) / n

    def profile(
        self,
        graph: nx.Graph,
        features: Sequence[str] | None = None,
    ) -> TopologyProfile:
        selected = resolve_profile_features(
            self.features if features is None else features
        )
        requested = set(selected)

        if graph.number_of_nodes() == 0:
            raise ValueError("cannot profile an empty graph")

        n = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        # Basic graph metadata is cheap and remains available in all profiles.
        density = float(nx.density(graph))

        needs_degree = bool(requested & _DEGREE_FEATURES)
        degrees: list[int] | None = None
        if needs_degree:
            degrees = [d for _, d in graph.degree()]
            avg = sum(degrees) / n
            std = math.sqrt(sum((d - avg) ** 2 for d in degrees) / n)
            max_degree = max(degrees)
            avg_degree = float(avg)
            degree_std = float(std)
            max_degree_value = int(max_degree)
            hub_ratio = float(max_degree / avg) if avg else 0.0
            degree_gini = self._gini([float(d) for d in degrees])
        else:
            avg_degree = float("nan")
            degree_std = float("nan")
            max_degree_value = 0
            hub_ratio = float("nan")
            degree_gini = float("nan")

        if "clustering" in requested:
            try:
                clustering = float(nx.average_clustering(graph))
            except Exception:
                clustering = float("nan")
        else:
            clustering = float("nan")

        if "transitivity" in requested:
            try:
                transitivity = float(nx.transitivity(graph))
            except Exception:
                transitivity = float("nan")
        else:
            transitivity = float("nan")

        if "assortativity" in requested:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    assortativity = float(nx.degree_assortativity_coefficient(graph))
            except Exception:
                assortativity = float("nan")
        else:
            assortativity = float("nan")

        if "core_number" in requested:
            try:
                core = float(max(nx.core_number(graph).values()))
            except Exception:
                core = float("nan")
        else:
            core = float("nan")

        if requested & _COMPONENT_FEATURES:
            components = list(nx.connected_components(graph))
            largest = graph.subgraph(max(components, key=len)).copy()
            if largest.number_of_nodes() > 1:
                if "diameter" in requested:
                    try:
                        diameter = float(nx.diameter(largest))
                    except Exception:
                        diameter = float("nan")
                else:
                    diameter = float("nan")
                if "avg_path_length" in requested:
                    try:
                        avg_path = float(
                            nx.average_shortest_path_length(largest)
                        )
                    except Exception:
                        avg_path = float("nan")
                else:
                    avg_path = float("nan")
            else:
                diameter = 0.0 if "diameter" in requested else float("nan")
                avg_path = 0.0 if "avg_path_length" in requested else float("nan")
        else:
            diameter = float("nan")
            avg_path = float("nan")

        communities = 0
        modularity = float("nan")
        if requested & _COMMUNITY_FEATURES:
            try:
                from networkx.algorithms.community import (
                    greedy_modularity_communities,
                    modularity as modularity_score,
                )

                detected = list(greedy_modularity_communities(graph))
                communities = len(detected)
                if "modularity" in requested and detected:
                    modularity = float(modularity_score(graph, detected))
            except Exception:
                pass

        return TopologyProfile(
            node_count=n,
            edge_count=edge_count,
            density=density,
            avg_degree=avg_degree,
            degree_std=degree_std,
            max_degree=max_degree_value,
            hub_ratio=hub_ratio,
            degree_gini=degree_gini,
            clustering=clustering,
            transitivity=transitivity,
            assortativity=assortativity,
            core_number=core,
            diameter=diameter,
            avg_path_length=avg_path,
            communities=communities,
            modularity=modularity,
        )
