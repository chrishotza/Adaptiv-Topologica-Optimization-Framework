from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from io import StringIO
from pathlib import Path
import sys

import networkx as nx

from .provenance import graph_fingerprint
from .selector import HeuristicRegimeSelector
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfile, TopologyProfiler


SUPPORTED_INPUT_FORMATS = ("auto", "edgelist", "json", "graphml", "gexf", "gml")
PARTITION_OUTPUT_FORMATS = ("auto", "json", "csv", "tsv")


def _validate_product_graph(graph: nx.Graph) -> None:
    """Validate the explicit graph contract used by the public product surface."""
    if graph.is_directed():
        raise ValueError("ATOF product mode requires an undirected graph")
    if graph.is_multigraph():
        raise ValueError("ATOF product mode requires a simple graph")
    if graph.number_of_nodes() < 2:
        raise ValueError("ATOF product mode requires at least 2 nodes")
    # Machine-readable partition outputs canonicalize node IDs with str().
    # Reject collisions such as 1 and "1" before serialization can merge them.
    serialized_ids = [str(node) for node in graph.nodes()]
    if len(serialized_ids) != len(set(serialized_ids)):
        raise ValueError(
            "ATOF product mode requires node IDs to be unique after string serialization"
        )
    # Edge attributes such as "weight" may be present in source graphs.
    # The current MVP graph model is explicitly unweighted, so these attributes
    # are ignored rather than interpreted as edge costs.


@dataclass(frozen=True)
class OptimizationResult:
    """Product-level result for one topology-aware partition run."""

    graph: nx.Graph
    topology: TopologyProfile
    regime: str
    requested_variant: str
    selected_variant: str
    k: int
    recommendation: str
    alternatives: tuple[str, ...]
    rationale: str
    partition_result: PartitionResult
    seed: int

    @property
    def selection_mode(self) -> str:
        return "heuristic" if self.requested_variant == "auto" else "explicit"

    @property
    def optimization_metric(self) -> str:
        """Name the scalar objective actually used by the selected variant."""
        if self.selected_variant == "affinity":
            return "degree_affinity_weighted_cut"
        return "edge_cut"

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
            "parameters": {
                "k": self.k,
                "seed": self.seed,
                "iterations": result.iterations,
            },
            "objective": {
                "reported_metric": "edge_cut",
                "optimization_metric": self.optimization_metric,
                "direction": "minimize",
                "graph_model": "unweighted",
                "variant_semantics": (
                    "affinity variant minimizes a degree-affinity weighted surrogate; "
                    "edge_cut remains the unweighted reported metric"
                    if self.selected_variant == "affinity"
                    else "baseline variant directly minimizes unweighted edge cut"
                ),
            },
            "provenance": {
                "graph_fingerprint": graph_fingerprint(self.graph),
                "backend": "BLOC-RELOC",
            },
            "topology": self.topology.to_dict(),
            "recommendation": {
                "primary": self.recommendation,
                "alternatives": list(self.alternatives),
                "rationale": self.rationale,
            },
            "result": {
                "k": self.k,
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


def _load_json_graph_payload(payload: object) -> nx.Graph:
    """Load ATOF's minimal JSON graph contract from a decoded payload."""
    if not isinstance(payload, dict):
        raise ValueError("JSON graph must be an object")
    edges = payload.get("edges", [])
    nodes = payload.get("nodes", [])
    if not isinstance(edges, list) or not isinstance(nodes, list):
        raise ValueError("JSON graph fields 'nodes' and 'edges' must be arrays")
    graph = nx.Graph()
    try:
        graph.add_nodes_from(nodes)
    except TypeError as exc:
        raise ValueError("JSON graph nodes must be hashable") from exc
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("JSON graph edges must be 2-item arrays")
        try:
            graph.add_edge(edge[0], edge[1])
        except TypeError as exc:
            raise ValueError("JSON graph edge endpoints must be hashable") from exc
    if not edges and not nodes:
        raise ValueError("JSON graph must contain at least one node or edge")
    return graph


def _load_json_graph(source: Path) -> nx.Graph:
    return _load_json_graph_payload(json.loads(source.read_text(encoding="utf-8")))


def load_graph(path: str | Path, format: str = "auto") -> nx.Graph:
    """Load an unweighted graph from a supported file format.

    Use "-" as the path to read an edge-list graph from stdin.
    """
    if str(path) == "-":
        if format not in {"auto", "edgelist", "json"}:
            raise ValueError("stdin input currently supports edge-list and JSON formats")
        if format == "json":
            graph = _load_json_graph_payload(json.loads(sys.stdin.read()))
        else:
            graph = nx.read_edgelist(StringIO(sys.stdin.read()), data=False)
        _validate_product_graph(graph)
        return graph

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if format not in SUPPORTED_INPUT_FORMATS:
        raise ValueError("format must be one of: " + ", ".join(SUPPORTED_INPUT_FORMATS))

    selected = format
    if selected == "auto":
        suffix = source.suffix.lower()
        selected = {
            ".json": "json",
            ".graphml": "graphml",
            ".gexf": "gexf",
            ".gml": "gml",
        }.get(suffix, "edgelist")

    if selected == "edgelist":
        graph = nx.read_edgelist(source, data=False)
    elif selected == "json":
        graph = _load_json_graph(source)
    elif selected == "graphml":
        graph = nx.read_graphml(source)
    elif selected == "gexf":
        graph = nx.read_gexf(source)
    else:
        graph = nx.read_gml(source)

    _validate_product_graph(graph)
    return graph


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
    if k < 2:
        raise ValueError("k must be at least 2")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    _validate_product_graph(graph)
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
        k=k,
        recommendation=recommendation.primary,
        alternatives=tuple(recommendation.alternatives),
        rationale=recommendation.rationale,
        partition_result=result,
        seed=seed,
    )


def write_partition_mapping(
    partition: dict,
    path: str | Path,
    *,
    format: str = "auto",
) -> Path:
    """Write any node-to-block mapping in a simple interoperable format."""
    target = Path(path)
    selected = format
    if selected == "auto":
        selected = {
            "json": "json",
            ".json": "json",
            ".csv": "csv",
            ".tsv": "tsv",
        }.get(target.suffix.lower(), "csv")
    if selected not in PARTITION_OUTPUT_FORMATS:
        raise ValueError("format must be one of: " + ", ".join(PARTITION_OUTPUT_FORMATS))

    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"node": str(node), "block": int(block)}
        for node, block in partition.items()
    ]
    rows.sort(key=lambda row: (row["block"], row["node"]))

    if selected == "json":
        target.write_text(
            json.dumps(rows, indent=2) + "\n",
            encoding="utf-8",
        )
        return target

    delimiter = "\t" if selected == "tsv" else ","
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("node", "block"), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return target


def write_partition(
    result: OptimizationResult,
    path: str | Path,
    *,
    format: str = "auto",
) -> Path:
    """Write the BLOC product partition in a simple interoperable format."""
    return write_partition_mapping(
        result.partition_result.partition,
        path,
        format=format,
    )
