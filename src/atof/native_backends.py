from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable

import networkx as nx

from .partition import balance_error


def write_metis_graph(graph: nx.Graph, path: str | Path) -> Path:
    """Write an unweighted simple graph in METIS adjacency-list format."""
    target = Path(path)
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}

    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(
            (index[neighbor] for neighbor in graph.neighbors(node)),
        )
        lines.append(" ".join(str(value) for value in neighbors))

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _validated_partition(
    graph: nx.Graph,
    membership: list[int],
    *,
    k: int,
) -> dict[Any, int]:
    if len(membership) != graph.number_of_nodes():
        raise ValueError("backend membership length does not match graph node count")

    nodes = list(graph.nodes())
    partition = {
        node: int(membership[index])
        for index, node in enumerate(nodes)
    }

    if any(block < 0 or block >= k for block in partition.values()):
        raise ValueError("backend returned an invalid block label")

    return partition


def run_kaminpar(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    quality: bool = False,
) -> tuple[dict[Any, int], int, float]:
    """Run KaMinPar through its official Python bindings."""
    import kaminpar

    context = (
        kaminpar.strong_context()
        if quality
        else kaminpar.default_context()
    )
    kaminpar.reseed(int(seed))
    instance = kaminpar.KaMinPar(num_threads=1, ctx=context)

    with tempfile.TemporaryDirectory(prefix="atof-kaminpar-") as directory:
        input_path = write_metis_graph(graph, Path(directory) / "graph.metis")
        backend_graph = kaminpar.load_graph(
            str(input_path),
            kaminpar.GraphFileFormat.METIS,
            compress=False,
        )
        max_block_factor = (graph.number_of_nodes() + k - 1) // k / graph.number_of_nodes()
        membership = list(
            instance.compute_partition(
                backend_graph,
                [max_block_factor] * k,
            )
        )

    partition = _validated_partition(graph, membership, k=k)
    return (
        partition,
        _edge_cut(graph, partition),
        balance_error(graph, partition, k),
    )


def run_mtkahypar(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    quality: bool = False,
) -> tuple[dict[Any, int], int, float]:
    """Run Mt-KaHyPar through its official Python bindings."""
    import mtkahypar

    initializer = mtkahypar.initialize(1, print_warnings=False)
    preset = (
        mtkahypar.PresetType.QUALITY
        if quality
        else mtkahypar.PresetType.DEFAULT
    )
    context = initializer.context_from_preset(preset)
    context.set_partitioning_parameters(k, 0.0, mtkahypar.Objective.CUT)
    context.logging = False
    mtkahypar.set_seed(int(seed))

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    edges = [
        (index[u], index[v])
        for u, v in graph.edges()
    ]

    backend_graph = initializer.create_graph(
        context,
        len(nodes),
        len(edges),
        edges,
    )
    partitioned_graph = backend_graph.partition(context)
    membership = [
        int(partitioned_graph.block_id(i))
        for i in range(len(nodes))
    ]

    partition = _validated_partition(graph, membership, k=k)
    return (
        partition,
        _edge_cut(graph, partition),
        balance_error(graph, partition, k),
    )


def _edge_cut(graph: nx.Graph, partition: dict[Any, int]) -> int:
    return sum(
        int(partition[u] != partition[v])
        for u, v in graph.edges()
    )


def backend_runners() -> dict[str, Callable[..., tuple[dict[Any, int], int, float]]]:
    """Return native backend runners keyed by stable ATOF backend IDs."""
    return {
        "kaminpar": lambda graph, seed, k: run_kaminpar(
            graph, seed=seed, k=k, quality=False
        ),
        "kaminpar-strong": lambda graph, seed, k: run_kaminpar(
            graph, seed=seed, k=k, quality=True
        ),
        "mtkahypar": lambda graph, seed, k: run_mtkahypar(
            graph, seed=seed, k=k, quality=False
        ),
        "mtkahypar-quality": lambda graph, seed, k: run_mtkahypar(
            graph, seed=seed, k=k, quality=True
        ),
    }
