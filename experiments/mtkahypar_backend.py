from __future__ import annotations

import tempfile
import time
from pathlib import Path

import networkx as nx

_GRAPH_CACHE: dict[tuple[str, str], object] = {}
_INITIALIZER = None
_TMPDIR = tempfile.TemporaryDirectory(prefix="atof-mtkahypar-")


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(index[neighbor] for neighbor in graph.neighbors(node))
        lines.append(" ".join(str(value) for value in neighbors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _initializer():
    global _INITIALIZER
    import mtkahypar

    if _INITIALIZER is None:
        _INITIALIZER = mtkahypar.initialize(1, print_warnings=False)
    return _INITIALIZER


def _preset(name: str):
    import mtkahypar

    presets = {
        "default": mtkahypar.PresetType.DEFAULT,
        "quality": mtkahypar.PresetType.QUALITY,
    }
    try:
        return presets[name]
    except KeyError as exc:
        raise ValueError(f"unknown Mt-KaHyPar preset: {name}") from exc


def _graph(graph: nx.Graph, graph_id: str, preset_name: str):
    import mtkahypar

    key = (graph_id, preset_name)
    cached = _GRAPH_CACHE.get(key)
    if cached is not None:
        return cached

    path = Path(_TMPDIR.name) / (
        graph_id.replace("/", "__").replace(" ", "_") + f"__{preset_name}.metis"
    )
    _write_metis_graph(graph, path)
    context = _initializer().context_from_preset(_preset(preset_name))
    loaded = _initializer().graph_from_file(
        str(path),
        context,
        mtkahypar.FileFormat.METIS,
    )
    _GRAPH_CACHE[key] = loaded
    return loaded


def run_mtkahypar(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    preset: str,
    epsilon: float,
) -> dict:
    import mtkahypar

    loaded = _graph(graph, graph_id, preset)
    context = _initializer().context_from_preset(_preset(preset))
    context.set_partitioning_parameters(
        int(k),
        float(epsilon),
        mtkahypar.Objective.CUT,
    )
    lower = graph.number_of_nodes() // k
    upper = (graph.number_of_nodes() + k - 1) // k
    num_upper = graph.number_of_nodes() - (lower * k)
    target_weights = [upper] * num_upper + [lower] * (k - num_upper)
    context.set_individual_target_block_weights(target_weights)

    mtkahypar.set_seed(int(seed))
    started = time.perf_counter()
    partitioned = loaded.partition(context)
    runtime = time.perf_counter() - started

    partition = [int(block) for block in partitioned.get_partition()]
    partition_map = {
        node: block for node, block in zip(graph.nodes(), partition)
    }
    edge_cut = sum(
        partition_map[u] != partition_map[v]
        for u, v in graph.edges()
    )

    return {
        "edge_cut": int(edge_cut),
        "balance_error": float(partitioned.imbalance(context)),
        "runtime_seconds": runtime,
        "metadata": {
            "preset": preset,
            "threads": 1,
            "seed_control": "mtkahypar.set_seed",
            "epsilon": float(epsilon),
            "target_block_weights": target_weights,
            "graph_load_in_timing": False,
            "backend_init_in_timing": False,
        },
    }
