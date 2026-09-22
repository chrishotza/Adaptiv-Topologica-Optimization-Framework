from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import networkx as nx

from .selector import HeuristicRegimeSelector
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfile, TopologyProfiler


_FORMATS = ("auto", "edgelist", "graphml", "gexf", "gml")


@dataclass(frozen=True)
class OptimizationResult:
    """Product-level result for one topology-aware partition run."""

    graph: nx.Graph
    topology: TopologyProfile
    regime: str
    requested_variant: str
    selected_variant: str
    recommendation: str
    alternatives: tuple[str, ...]
    rationale: str
    partition_result: PartitionResult

    @property
    def selection_mode(self) -> str:
        return "heuristic" if self.requested_variant == "auto" else "explicit"

    def to_dict(self, *, include_partition: bool = True) -> dict:
        result = self.partition_result
        block_sizes: dict[str, int] = {}
        for block in result.partition.values():
            key = str(block)
            block_sizes[key] = block_sizes.get(key, 0) + 1

        payload = {
            "mode": "optimize",
            "strategy": {
                "requested": self.requested_variant,
                "selected": f"BLOCReloc({self.selected_variant})",
                "selection_mode": self.selection_mode,
                "regime": self.regime,
            },
            "graph": {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
            },
            "topology": self.topology.to_dict(),
            "recommendation": {
                "primary": self.recommendation,
                "alternatives": list(self.alternatives),
                "rationale": self.rationale,
            },
            "result": {
                "k": result.iterations and None,
                "iterations": result.iterations,
                "edge_cut": result.edge_cut,
                "weighted_cost": result.weighted_cost,
                "balance_error": result.balance_error,
                "accepted_moves": result.accepted_moves,
                "rejected_moves": result.rejected_moves,
                "block_sizes": block_sizes,
            },
        }
        if include_partition:
            payload["result"]["partition"] = {
                str(node): block for node, block in result.partition.items()
            }
        return payload


def load_graph(path: str | Path, format: str = "auto") -> nx.Graph:
    """Load an unweighted graph from a supported file format."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if format not in _FORMATS:
        raise ValueError("format must be one of: " + ", ".join(_FORMATS))

    selected = format
    if selected == "auto":
        suffix = source.suffix.lower()
        selected = {
            ".graphml": "graphml",
            ".gexf": "gexf",
            ".gml": "gml",
        }.get(suffix, "edgelist")

    if selected == "edgelist":
        graph = nx.read_edgelist(source, data=False)
    elif selected == "graphml":
        graph = nx.read_graphml(source)
    elif selected == "gexf":
        graph = nx.read_gexf(source)
    else:
        graph = nx.read_gml(source)

    return nx.Graph(graph)


def _select_variant(recommendation: str) -> str:
    return "affinity" if recommendation.endswith("(affinity)") else "baseline"


def optimize_graph(
    graph: nx.Graph,
    *,
    k: int = 2,
    seed: int = 42,
    iterations: int = 25,
    variant: str = "auto",
) -> OptimizationResult:
    """Profile and partition a graph with the product selection policy."""
    if variant not in ("auto", "baseline", "affinity"):
        raise ValueError("variant must be one of: auto, baseline, affinity")

    profiler = TopologyProfiler()
    topology = profiler.profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(topology)
    selected = _select_variant(recommendation.primary) if variant == "auto" else variant

    result = BLOCReloc(
        graph,
        k=k,
        seed=seed,
        variant=selected,
    ).refine(iterations=iterations)

    return OptimizationResult(
        graph=graph,
        topology=topology,
        regime=recommendation.regime,
        requested_variant=variant,
        selected_variant=selected,
        recommendation=recommendation.primary,
        alternatives=tuple(recommendation.alternatives),
        rationale=recommendation.rationale,
        partition_result=result,
    )