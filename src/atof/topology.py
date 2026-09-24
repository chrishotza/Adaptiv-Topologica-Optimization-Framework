from __future__ import annotations
import math
import warnings
from dataclasses import dataclass, asdict
from typing import Any
import networkx as nx

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
    """Compute interpretable structural descriptors for a graph."""
    @staticmethod
    def _gini(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values); total = sum(ordered); n = len(ordered)
        if total == 0:
            return 0.0
        weighted = sum((i + 1) * value for i, value in enumerate(ordered))
        return (2 * weighted) / (n * total) - (n + 1) / n

    def profile(self, graph: nx.Graph) -> TopologyProfile:
        if graph.number_of_nodes() == 0:
            raise ValueError("cannot profile an empty graph")
        degrees = [d for _, d in graph.degree()]
        n = graph.number_of_nodes()
        avg = sum(degrees) / n
        std = math.sqrt(sum((d - avg) ** 2 for d in degrees) / n)
        max_degree = max(degrees)
        components = list(nx.connected_components(graph))
        largest = graph.subgraph(max(components, key=len)).copy()
        try: clustering = float(nx.average_clustering(graph))
        except Exception: clustering = float("nan")
        try: transitivity = float(nx.transitivity(graph))
        except Exception: transitivity = float("nan")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                assortativity = float(nx.degree_assortativity_coefficient(graph))
        except Exception:
            assortativity = float("nan")
        try: core = float(max(nx.core_number(graph).values()))
        except Exception: core = float("nan")
        if largest.number_of_nodes() > 1:
            try: diameter = float(nx.diameter(largest))
            except Exception: diameter = float("nan")
            try: avg_path = float(nx.average_shortest_path_length(largest))
            except Exception: avg_path = float("nan")
        else:
            diameter = 0.0; avg_path = 0.0
        communities = 0; modularity = float("nan")
        try:
            from networkx.algorithms.community import greedy_modularity_communities, modularity
            detected = list(greedy_modularity_communities(graph))
            communities = len(detected)
            if detected: modularity = float(modularity(graph, detected))
        except Exception:
            pass
        return TopologyProfile(
            node_count=n, edge_count=graph.number_of_edges(), density=float(nx.density(graph)),
            avg_degree=float(avg), degree_std=float(std), max_degree=int(max_degree),
            hub_ratio=float(max_degree / avg) if avg else 0.0,
            degree_gini=self._gini([float(d) for d in degrees]), clustering=clustering,
            transitivity=transitivity, assortativity=assortativity, core_number=core,
            diameter=diameter, avg_path_length=avg_path, communities=communities,
            modularity=modularity,
        )
