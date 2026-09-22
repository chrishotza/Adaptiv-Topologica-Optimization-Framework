from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Any, Callable

import networkx as nx

from .provenance import graph_fingerprint, package_version
from .backends import run_kaminpar, run_mtkahypar
from .partition import (
    balance_error as partition_balance_error,
    exact_balanced_block_weights,
    rebalance_kway,
)
from .product import validate_product_graph
from .selector import HeuristicRegimeSelector
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfile, TopologyProfiler


@dataclass(frozen=True)
class PortfolioCandidate:
    id: str
    name: str
    available: bool
    edge_cut: int | None
    balance_error: float | None
    runtime_seconds: float | None
    partition: dict[Any, int] | None
    backend_version: str | None
    postprocess: str
    error: str | None = None

    def to_dict(self, *, include_partition: bool = False) -> dict:
        payload = {
            "id": self.id,
            "name": self.name,
            "available": self.available,
            "edge_cut": self.edge_cut,
            "balance_error": self.balance_error,
            "runtime_seconds": self.runtime_seconds,
            "backend_version": self.backend_version,
            "postprocess": self.postprocess,
            "error": self.error,
        }
        if include_partition and self.partition is not None:
            payload["partition"] = {
                str(node): int(block) for node, block in self.partition.items()
            }
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
    seed: int
    iterations: int
    graph_fingerprint: str
    selection_policy: str = "empirical_min_edge_cut"

    def to_dict(self, *, include_partition: bool = True) -> dict:
        payload = {
            "schema": "atof.portfolio.v1",
            "version": package_version("atof"),
            "mode": "portfolio",
            "strategy": {
                "selected": self.selected_strategy,
                "regime": self.regime,
                "selection_policy": self.selection_policy,
            },
            "graph": {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
            },
            "parameters": {
                "k": self.k,
                "seed": self.seed,
                "iterations": self.iterations,
            },
            "objective": {
                "name": "edge_cut",
                "direction": "minimize",
                "graph_model": "unweighted_undirected",
                "balance": "balanced k-way partition",
            },
            "topology": self.topology.to_dict(),
            "result": {
                "k": self.k,
                "edge_cut": self.selected_edge_cut,
                "balance_error": self.selected_balance_error,
            },
            "provenance": {
                "graph_fingerprint": self.graph_fingerprint,
                "available_backends": [
                    candidate.id
                    for candidate in self.candidates
                    if candidate.available
                ],
                "postprocessing": {
                    candidate.id: candidate.postprocess
                    for candidate in self.candidates
                    if candidate.available
                },
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


def _rebalance_kway(
    graph: nx.Graph,
    membership: list[int],
    k: int,
) -> list[int]:
    """Backward-compatible wrapper around the shared k-way repair contract."""
    return rebalance_kway(graph, membership, k)



def _run_bloc(
    graph: nx.Graph,
    *,
    seed: int,
    iterations: int,
    variant: str,
    k: int,
) -> tuple[dict[Any, int], int, float]:
    result: PartitionResult = BLOCReloc(
        graph,
        k=k,
        seed=seed,
        variant=variant,
    ).refine(iterations=iterations)
    return result.partition, int(result.edge_cut), float(result.balance_error)


def _run_kernighan_lin(
    graph: nx.Graph,
    *,
    seed: int,
    iterations: int,
    k: int,
) -> tuple[dict[Any, int], int, float]:
    if k != 2:
        raise ValueError("NetworkX Kernighan-Lin supports only k=2")

    from networkx.algorithms.community import kernighan_lin_bisection

    left, right = kernighan_lin_bisection(
        graph,
        partition=None,
        max_iter=max(1, iterations),
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
    k: int,
) -> tuple[dict[Any, int], int, float]:
    import pymetis

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = [
        [index[neighbor] for neighbor in graph.neighbors(node)]
        for node in nodes
    ]
    raw = pymetis.part_graph(
        k,
        adjacency=adjacency,
        tpwgts=[1.0 / k] * k,
        recursive=True,
        options=pymetis.Options(seed=seed),
    )
    membership = _rebalance_kway(graph, list(raw.vertex_part), k)
    partition = {node: membership[index[node]] for node in nodes}
    return (
        partition,
        _edge_cut(graph, partition),
        partition_balance_error(graph, partition, k),
    )


def _run_kahip(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
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
        k,
        0.03,
        1,
        int(seed),
        2,
    )
    membership = _rebalance_kway(graph, [int(block) for block in raw_membership], k)
    partition = {node: membership[index[node]] for node in nodes}
    return (
        partition,
        _edge_cut(graph, partition),
        partition_balance_error(graph, partition, k),
    )



def _run_kaminpar(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    context_name: str,
) -> tuple[dict[Any, int], int, float]:
    partition, edge_cut, balance, _runtime = run_kaminpar(
        graph,
        graph_id=graph_fingerprint(graph),
        seed=seed,
        k=k,
        context_name=context_name,
    )
    return partition, edge_cut, balance


def _run_mtkahypar(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    preset: str,
) -> tuple[dict[Any, int], int, float]:
    partition, edge_cut, balance, _runtime = run_mtkahypar(
        graph,
        graph_id=graph_fingerprint(graph),
        seed=seed,
        k=k,
        preset=preset,
    )
    return partition, edge_cut, balance


def _validate_candidate_partition(
    graph: nx.Graph,
    k: int,
    candidate: PortfolioCandidate,
) -> PortfolioCandidate:
    """Validate and canonicalize one backend result against the product contract."""
    if not candidate.available or candidate.partition is None:
        return candidate

    try:
        graph_nodes = set(graph.nodes())
        partition_nodes = set(candidate.partition)
        if partition_nodes != graph_nodes:
            missing = graph_nodes - partition_nodes
            extra = partition_nodes - graph_nodes
            raise ValueError(
                "partition node coverage mismatch"
                f"; missing={len(missing)}, extra={len(extra)}"
            )

        labels = tuple(candidate.partition.values())
        if any(not isinstance(block, int) or isinstance(block, bool) for block in labels):
            raise ValueError("partition labels must be integers")
        if any(block < 0 or block >= k for block in labels):
            raise ValueError("partition labels must be in [0, k)")

        edge_cut = _edge_cut(graph, candidate.partition)
        target_weights = exact_balanced_block_weights(
            graph.number_of_nodes(),
            k,
        )
        counts = [
            sum(1 for block in labels if block == target)
            for target in range(k)
        ]
        if sorted(counts) != sorted(target_weights):
            raise ValueError(
                "partition violates exact floor/ceil balance contract"
            )
        balance = partition_balance_error(graph, candidate.partition, k)
        postprocess = candidate.postprocess
        if postprocess == "none":
            postprocess = "contract_validation"
        elif "contract_validation" not in postprocess:
            postprocess = f"{postprocess};contract_validation"

        return replace(
            candidate,
            edge_cut=edge_cut,
            balance_error=balance,
            postprocess=postprocess,
            error=None,
        )
    except Exception as exc:
        return replace(
            candidate,
            available=False,
            edge_cut=None,
            balance_error=None,
            runtime_seconds=candidate.runtime_seconds,
            partition=None,
            postprocess="contract_validation_failed",
            error=f"{type(exc).__name__}: {exc}",
        )


def _candidate(
    *,
    backend_id: str,
    name: str,
    package: str,
    postprocess: str,
    runner: Callable[[], tuple[dict[Any, int], int, float]],
) -> PortfolioCandidate:
    started = time.perf_counter()
    try:
        partition, edge_cut, balance_error = runner()
        return PortfolioCandidate(
            id=backend_id,
            name=name,
            available=True,
            edge_cut=edge_cut,
            balance_error=balance_error,
            runtime_seconds=time.perf_counter() - started,
            partition=partition,
            backend_version=package_version(package),
            postprocess=postprocess,
        )
    except ImportError as exc:
        return PortfolioCandidate(
            id=backend_id,
            name=name,
            available=False,
            edge_cut=None,
            balance_error=None,
            runtime_seconds=None,
            partition=None,
            backend_version=package_version(package),
            postprocess=postprocess,
            error=f"optional dependency unavailable: {exc}",
        )
    except Exception as exc:
        return PortfolioCandidate(
            id=backend_id,
            name=name,
            available=False,
            edge_cut=None,
            balance_error=None,
            runtime_seconds=time.perf_counter() - started,
            partition=None,
            backend_version=package_version(package),
            postprocess=postprocess,
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
    """Evaluate available open-source backends under one auditable contract."""
    if k < 2:
        raise ValueError("portfolio mode requires k>=2")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if k > graph.number_of_nodes():
        raise ValueError("k cannot exceed the number of graph nodes")
    validate_product_graph(graph)

    topology = TopologyProfiler().profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(topology)

    candidates = [
        _candidate(
            backend_id="bloc",
            name="BLOCReloc(baseline)",
            package="atof",
            postprocess="none",
            runner=lambda: _run_bloc(
                graph,
                seed=seed,
                iterations=iterations,
                variant="baseline",
                k=k,
            ),
        ),
        _candidate(
            backend_id="bloc-affinity",
            name="BLOCReloc(affinity)",
            package="atof",
            postprocess="none",
            runner=lambda: _run_bloc(
                graph,
                seed=seed,
                iterations=iterations,
                variant="affinity",
                k=k,
            ),
        ),
        (
            _candidate(
                backend_id="networkx-kl",
                name="NetworkX(Kernighan-Lin)",
                package="networkx",
                postprocess="none",
                runner=lambda: _run_kernighan_lin(
                    graph,
                    seed=seed,
                    iterations=iterations,
                    k=k,
                ),
            )
            if k == 2
            else PortfolioCandidate(
                id="networkx-kl",
                name="NetworkX(Kernighan-Lin)",
                available=False,
                edge_cut=None,
                balance_error=None,
                runtime_seconds=None,
                partition=None,
                backend_version=package_version("networkx"),
                postprocess="not_applicable_for_k_way",
                error="NetworkX Kernighan-Lin supports only k=2",
            )
        ),
    ]

    if include_optional:
        candidates.extend(
            [
                _candidate(
                    backend_id="metis",
                    name="METIS(PyMetis)",
                    package="pymetis",
                    postprocess="balance_repair",
                    runner=lambda: _run_metis(graph, seed=seed, k=k),
                ),
                _candidate(
                    backend_id="kahip",
                    name="KaHIP(KaFFPa-Strong)",
                    package="kahip",
                    postprocess="balance_repair",
                    runner=lambda: _run_kahip(graph, seed=seed, k=k),
                ),
                _candidate(
                    backend_id="kaminpar-default",
                    name="KaMinPar(default)",
                    package="kaminpar",
                    postprocess="none",
                    runner=lambda: _run_kaminpar(
                        graph,
                        seed=seed,
                        k=k,
                        context_name="default",
                    ),
                ),
                _candidate(
                    backend_id="kaminpar-strong",
                    name="KaMinPar(strong)",
                    package="kaminpar",
                    postprocess="none",
                    runner=lambda: _run_kaminpar(
                        graph,
                        seed=seed,
                        k=k,
                        context_name="strong",
                    ),
                ),
                _candidate(
                    backend_id="mtkahypar-default",
                    name="Mt-KaHyPar(default)",
                    package="mtkahypar",
                    postprocess="none",
                    runner=lambda: _run_mtkahypar(
                        graph,
                        seed=seed,
                        k=k,
                        preset="default",
                    ),
                ),
                _candidate(
                    backend_id="mtkahypar-quality",
                    name="Mt-KaHyPar(quality)",
                    package="mtkahypar",
                    postprocess="none",
                    runner=lambda: _run_mtkahypar(
                        graph,
                        seed=seed,
                        k=k,
                        preset="quality",
                    ),
                ),
            ]
        )

    candidates = [
        _validate_candidate_partition(graph, k, candidate)
        for candidate in candidates
    ]

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
        seed=seed,
        iterations=iterations,
        graph_fingerprint=graph_fingerprint(graph),
    )
