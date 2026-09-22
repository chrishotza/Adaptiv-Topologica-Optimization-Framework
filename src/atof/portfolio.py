from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

import networkx as nx

from .product import load_graph
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfile, TopologyProfiler
from .selector import HeuristicRegimeSelector


@dataclass(frozen=True)
class PortfolioCandidate:
    name: str
    available: bool
    edge_cut: int | None
    balance_error: float | None
    runtime_seconds: float | None
    partition: dict[Any, int] | None
    error: str | None = None

    def to_dict(self, *, include_partition: bool = False) -> dict:
        payload = {
            "name": self.name,
            "available": self.available,
            "edge_cut": self.edge_cut,
            "balance_error": self.balance_error,
            "runtime_seconds": self.runtime_seconds,
            "error": self.error,
        }
        if include_partition and self.partition is not None:
            payload["partition"] = {str(node): int(block) for node, block in self.partition.items()}
        return payload


@dataclass(frozen=True)
class PortfolioOptimizationResult:
    graph: nx.Graph
    topology: TopologyProfile
    regime: str
    selected_strategy: str
    selected_partition: dict[Any, int]
    selected_edge_cut: int
    selected_balance_error: float
    candidates: tuple[PortfolioCandidate, ...]
    k: int

    def to_dict(self, *, include_partition: bool = True) -> dict:
        payload = {
            "mode": "portfolio",
            "strategy": {
                "selected": self.selected_strategy,
                "regime": self.regime,
            },
            "graph": {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
            },
            "topology": self.topology.to_dict(),
            "result": {
                "k": self.k,
                "edge_cut": self.selected_edge_cut,
                "balance_error": self.selected_balance_error,
            },
            "candidates": [
                candidate.to_dict(include_partition=False)
                for candidate in self.candidates
            ],
        }
        if include_partition:
            payload["result"]["partition"] = {
                str(node): int(block)
                for node, block in self.selected_partition.items()
            }
        return payload


def _edge_cut(graph: nx.Graph, partition: dict[Any, int]) -> int:
    return sum(partition[u] != partition[v] for u, v in graph.edges())


def _rebalance_two_way(
    graph: nx.Graph,
    membership: list[int],
) -> list[int]:
    if len(membership) != graph.number_of_nodes():
        raise ValueError("membership length must match graph node count")
    if set(membership) - {0, 1}:
        raise ValueError("membership must contain only 0 and 1")

    target_zero = graph.number_of_nodes() // 2
    current_zero = membership.count(0)
    if current_zero == target_zero:
        return list(membership)

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    result = list(membership)
    source = 0 if current_zero > target_zero else 1
    target = 1 - source
    moves = abs(current_zero - target_zero)

    for _ in range(moves):
        candidates: list[tuple[int, str, int]] = []
        for node in nodes:
            i = index[node]
            if result[i] != source:
                continue
            source_neighbors = sum(
                1
                for neighbor in graph.neighbors(node)
                if result[index[neighbor]] == source
            )
            target_neighbors = graph.degree(node) - source_neighbors
            delta = source_neighbors - target_neighbors
            candidates.append((delta, repr(node), i))
        if not candidates:
            raise RuntimeError("could not repair partition balance")
        _, _, chosen = min(candidates)
        result[chosen] = target

    return result


def _run_bloc(
    graph: nx.Graph,
    *,
    seed: int,
    iterations: int,
    variant: str,
) -> tuple[dict[Any, int], int, float]:
    result: PartitionResult = BLOCReloc(
        graph,
        k=2,
        seed=seed,
        variant=variant,
    ).refine(iterations=iterations)
    return result.partition, int(result.edge_cut), float(result.balance_error)


def _run_kernighan_lin(
    graph: nx.Graph,
    *,
    seed: int,
    iterations: int,
) -> tuple[dict[Any, int], int, float]:
    del iterations
    from networkx.algorithms.community import kernighan_lin_bisection

    left, right = kernighan_lin_bisection(
        graph,
        partition=None,
        max_iter=25,
        weight=None,
        seed=seed,
    )
    left = set(left)
    partition = {node: (0 if node in left else 1) for node in graph.nodes()}
    balance_error = abs(len(left) - len(right)) / graph.number_of_nodes()
    return partition, _edge_cut(graph, partition), float(balance_error)


def _run_metis(
    graph: nx.Graph,
    *,
    seed: int,
) -> tuple[dict[Any, int], int, float]:
    import pymetis

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = [
        [index[neighbor] for neighbor in graph.neighbors(node)]
        for node in nodes
    ]
    raw = pymetis.part_graph(
        2,
        adjacency=adjacency,
        tpwgts=[0.5, 0.5],
        recursive=True,
        options=pymetis.Options(seed=seed),
    )
    membership = _rebalance_two_way(graph, list(raw.vertex_part))
    partition = {node: membership[index[node]] for node in nodes}
    return partition, _edge_cut(graph, partition), abs(membership.count(0) - membership.count(1)) / len(nodes)


def _run_kahip(
    graph: nx.Graph,
    *,
    seed: int,
) -> tuple[dict[Any, int], int, float]:
    import kahip

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    xadj = [0]
    adjncy: list[int] = []
    for node in nodes:
        adjncy.extend(index[neighbor] for neighbor in graph.neighbors(node))
        xadj.append(len(adjncy))
    _, raw_membership = kahip.kaffpa(
        [1] * len(nodes),
        xadj,
        [1] * len(adjncy),
        adjncy,
        2,
        0.03,
        1,
        int(seed),
        2,
    )
    membership = _rebalance_two_way(graph, [int(block) for block in raw_membership])
    partition = {node: membership[index[node]] for node in nodes}
    return partition, _edge_cut(graph, partition), abs(membership.count(0) - membership.count(1)) / len(nodes)


def _candidate(
    name: str,
    runner: Callable[[], tuple[dict[Any, int], int, float]],
) -> PortfolioCandidate:
    started = time.perf_counter()
    try:
        partition, edge_cut, balance_error = runner()
        return PortfolioCandidate(
            name=name,
            available=True,
            edge_cut=edge_cut,
            balance_error=balance_error,
            runtime_seconds=time.perf_counter() - started,
            partition=partition,
        )
    except ImportError as exc:
        return PortfolioCandidate(
            name=name,
            available=False,
            edge_cut=None,
            balance_error=None,
            runtime_seconds=None,
            partition=None,
            error=f"optional dependency unavailable: {exc}",
        )
    except Exception as exc:
        return PortfolioCandidate(
            name=name,
            available=False,
            edge_cut=None,
            balance_error=None,
            runtime_seconds=time.perf_counter() - started,
            partition=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def optimize_portfolio(
    graph: nx.Graph,
    *,
    k: int = 2,
    seed: int = 42,
    iterations: int = 25,
    include_optional: bool = True,
) -> PortfolioOptimizationResult:
    """Evaluate available open-source partitioning backends under one product contract.

    For k=2 the portfolio can evaluate BLOC-RELOC, NetworkX Kernighan-Lin,
    and optional PyMetis/KaHIP backends. The selected result minimizes
    edge cut subject to the same two-way balance contract.

    The portfolio is empirical rather than a claim of universal optimality.
    """
    if k != 2:
        raise ValueError("portfolio mode currently supports k=2")

    profiler = TopologyProfiler()
    topology = profiler.profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(topology)

    candidates = [
        _candidate(
            "BLOCReloc(baseline)",
            lambda: _run_bloc(
                graph,
                seed=seed,
                iterations=iterations,
                variant="baseline",
            ),
        ),
        _candidate(
            "BLOCReloc(affinity)",
            lambda: _run_bloc(
                graph,
                seed=seed,
                iterations=iterations,
                variant="affinity",
            ),
        ),
        _candidate(
            "NetworkX(Kernighan-Lin)",
            lambda: _run_kernighan_lin(
                graph,
                seed=seed,
                iterations=iterations,
            ),
        ),
    ]

    if include_optional:
        candidates.extend(
            [
                _candidate(
                    "METIS(PyMetis)",
                    lambda: _run_metis(graph, seed=seed),
                ),
                _candidate(
                    "KaHIP(KaFFPa-Strong)",
                    lambda: _run_kahip(graph, seed=seed),
                ),
            ]
        )

    available = [
        candidate
        for candidate in candidates
        if candidate.available and candidate.partition is not None
    ]
    if not available:
        raise RuntimeError("no portfolio backend produced a result")

    selected = min(
        available,
        key=lambda candidate: (
            float(candidate.edge_cut),
            float(candidate.balance_error),
            float(candidate.runtime_seconds),
            candidate.name,
        ),
    )

    return PortfolioOptimizationResult(
        graph=graph,
        topology=topology,
        regime=recommendation.regime,
        selected_strategy=selected.name,
        selected_partition=dict(selected.partition),
        selected_edge_cut=int(selected.edge_cut),
        selected_balance_error=float(selected.balance_error),
        candidates=tuple(candidates),
        k=k,
    )
