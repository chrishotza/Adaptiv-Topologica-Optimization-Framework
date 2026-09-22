from __future__ import annotations

import math
import os
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from multiprocessing import get_context
from typing import Any

import networkx as nx


AVERAGE_PATH_PARALLEL_THRESHOLD = 2_000
AVERAGE_PATH_MAX_WORKERS = 4
_AVERAGE_PATH_ADJ = None


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


def _sum_source_distances(source: Any) -> int:
    adjacency = _AVERAGE_PATH_ADJ
    if adjacency is None:
        raise RuntimeError("parallel shortest-path adjacency is not initialized")

    distances = {source: 0}
    queue = deque([source])
    total = 0
    while queue:
        node = queue.popleft()
        distance = distances[node]
        for neighbor in adjacency[node]:
            if neighbor not in distances:
                next_distance = distance + 1
                distances[neighbor] = next_distance
                total += next_distance
                queue.append(neighbor)
    return total


def _sum_source_chunk(sources: tuple[Any, ...]) -> int:
    return sum(_sum_source_distances(source) for source in sources)


def _chunked(values: list[Any], chunks: int) -> list[tuple[Any, ...]]:
    if not values:
        return []
    chunks = max(1, min(chunks, len(values)))
    size = math.ceil(len(values) / chunks)
    return [
        tuple(values[index:index + size])
        for index in range(0, len(values), size)
    ]


def _average_shortest_path_length_exact(graph: nx.Graph) -> float:
    """
    Compute the exact unweighted average shortest-path length.

    For large graphs on fork-capable platforms, source BFS runs in parallel
    while sharing the read-only NetworkX adjacency structure via copy-on-write.
    The arithmetic remains exact for integer distances; only the final division
    produces the floating-point result.
    """
    node_count = graph.number_of_nodes()
    if node_count <= 1:
        return 0.0

    if node_count < AVERAGE_PATH_PARALLEL_THRESHOLD:
        return float(nx.average_shortest_path_length(graph))

    if "fork" not in get_context.__globals__.get("__builtins__", {}):
        return float(nx.average_shortest_path_length(graph))

    try:
        context = get_context("fork")
    except (ValueError, AttributeError):
        return float(nx.average_shortest_path_length(graph))

    workers = min(
        AVERAGE_PATH_MAX_WORKERS,
        max(1, os.cpu_count() or 1),
        node_count,
    )
    if workers <= 1:
        return float(nx.average_shortest_path_length(graph))

    global _AVERAGE_PATH_ADJ
    _AVERAGE_PATH_ADJ = graph.adj
    try:
        sources = list(graph.nodes)
        source_chunks = _chunked(sources, workers)
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
        ) as executor:
            totals = executor.map(_sum_source_chunk, source_chunks)
            total_distance = sum(totals)
    finally:
        _AVERAGE_PATH_ADJ = None

    return total_distance / (node_count * (node_count - 1))


class TopologyProfiler:
    """Compute interpretable structural descriptors for a graph."""

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

        try:
            clustering = float(nx.average_clustering(graph))
        except Exception:
            clustering = float("nan")
        try:
            transitivity = float(nx.transitivity(graph))
        except Exception:
            transitivity = float("nan")
        try:
            assortativity = float(nx.degree_assortativity_coefficient(graph))
        except Exception:
            assortativity = float("nan")
        try:
            core = float(max(nx.core_number(graph).values()))
        except Exception:
            core = float("nan")

        if largest.number_of_nodes() > 1:
            try:
                diameter = float(nx.diameter(largest, usebounds=True))
            except Exception:
                diameter = float("nan")
            try:
                avg_path = _average_shortest_path_length_exact(largest)
            except Exception:
                avg_path = float("nan")
        else:
            diameter = 0.0
            avg_path = 0.0

        communities = 0
        modularity = float("nan")
        try:
            from networkx.algorithms.community import (
                greedy_modularity_communities,
                modularity,
            )

            detected = list(greedy_modularity_communities(graph))
            communities = len(detected)
            if detected:
                modularity = float(modularity(graph, detected))
        except Exception:
            pass

        return TopologyProfile(
            node_count=n,
            edge_count=graph.number_of_edges(),
            density=float(nx.density(graph)),
            avg_degree=float(avg),
            degree_std=float(std),
            max_degree=int(max_degree),
            hub_ratio=float(max_degree / avg) if avg else 0.0,
            degree_gini=self._gini([float(d) for d in degrees]),
            clustering=clustering,
            transitivity=transitivity,
            assortativity=assortativity,
            core_number=core,
            diameter=diameter,
            avg_path_length=avg_path,
            communities=communities,
            modularity=modularity,
        )
