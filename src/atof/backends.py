from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import pickle
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import networkx as nx

from .partition import balance_error as partition_balance_error
from .provenance import package_version


@dataclass(frozen=True)
class BackendInfo:
    id: str
    name: str
    package: str
    optional: bool
    available: bool
    version: str | None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_SPECS = (
    ("bloc", "BLOC-RELOC", "atof", False),
    ("networkx-kl", "NetworkX Kernighan-Lin", "networkx", False),
    ("metis", "METIS via PyMetis", "pymetis", True),
    ("kahip", "KaHIP via KaFFPa-Strong", "kahip", True),
    ("kaminpar-default", "KaMinPar default", "kaminpar", True),
    ("kaminpar-strong", "KaMinPar strong", "kaminpar", True),
    ("mtkahypar-default", "Mt-KaHyPar default", "mtkahypar", True),
    ("mtkahypar-quality", "Mt-KaHyPar quality", "mtkahypar", True),
)

_TMPDIR = tempfile.TemporaryDirectory(prefix="atof-backends-")


def inspect_backends(*, include_optional: bool = True) -> tuple[BackendInfo, ...]:
    results: list[BackendInfo] = []
    for backend_id, name, package, optional in _SPECS:
        if optional and not include_optional:
            continue
        version = package_version(package)
        if version is None:
            results.append(
                BackendInfo(
                    id=backend_id,
                    name=name,
                    package=package,
                    optional=optional,
                    available=False,
                    version=None,
                    error="package not installed",
                )
            )
            continue
        results.append(
            BackendInfo(
                id=backend_id,
                name=name,
                package=package,
                optional=optional,
                available=True,
                version=version,
            )
        )
    return tuple(results)


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(index[neighbor] for neighbor in graph.neighbors(node))
        lines.append(" ".join(str(value) for value in neighbors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _partition_metrics(
    graph: nx.Graph,
    partition: dict[Any, int],
    k: int,
) -> tuple[int, float]:
    edge_cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return int(edge_cut), float(partition_balance_error(graph, partition, k))


_KAMINPAR_CONTEXTS: dict[str, object] = {}
_KAMINPAR_GRAPHS: dict[str, object] = {}
_MTKAHYPAR_INITIALIZER: object | None = None


def _kaminpar_context(context_name: str):
    import kaminpar

    cached = _KAMINPAR_CONTEXTS.get(context_name)
    if cached is not None:
        return cached
    factory = {
        "default": kaminpar.default_context,
        "strong": kaminpar.strong_context,
    }.get(context_name)
    if factory is None:
        raise ValueError(f"unknown KaMinPar context: {context_name}")
    context = factory()
    instance = kaminpar.KaMinPar(1, context)
    _KAMINPAR_CONTEXTS[context_name] = instance
    return instance


def _kaminpar_graph(graph: nx.Graph, graph_id: str):
    import kaminpar

    cached = _KAMINPAR_GRAPHS.get(graph_id)
    if cached is not None:
        return cached
    path = Path(_TMPDIR.name) / (
        graph_id.replace("/", "__").replace(" ", "_") + ".metis"
    )
    _write_metis_graph(graph, path)
    loaded = kaminpar.load_graph(
        str(path),
        kaminpar.GraphFileFormat.METIS,
        compress=False,
    )
    _KAMINPAR_GRAPHS[graph_id] = loaded
    return loaded


def _run_kaminpar_in_process(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    context_name: str,
) -> tuple[dict[Any, int], int, float, float]:
    import kaminpar

    loaded = _kaminpar_graph(graph, graph_id)
    instance = _kaminpar_context(context_name)
    max_block_weight = (graph.number_of_nodes() + k - 1) // k
    kaminpar.reseed(int(seed))
    started = time.perf_counter()
    membership = instance.compute_partition(
        loaded,
        max_block_weights=[max_block_weight] * k,
    )
    runtime = time.perf_counter() - started
    partition = {
        node: int(block)
        for node, block in zip(graph.nodes(), membership)
    }
    edge_cut, balance = _partition_metrics(graph, partition, k)
    return partition, edge_cut, balance, runtime


def _mtkahypar_initializer():
    global _MTKAHYPAR_INITIALIZER
    import mtkahypar

    if _MTKAHYPAR_INITIALIZER is None:
        _MTKAHYPAR_INITIALIZER = mtkahypar.initialize(1, print_warnings=False)
    return _MTKAHYPAR_INITIALIZER


def _mtkahypar_preset(name: str):
    import mtkahypar

    presets = {
        "default": mtkahypar.PresetType.DEFAULT,
        "quality": mtkahypar.PresetType.QUALITY,
    }
    try:
        return presets[name]
    except KeyError as exc:
        raise ValueError(f"unknown Mt-KaHyPar preset: {name}") from exc


def _run_mtkahypar_in_process(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    preset: str,
) -> tuple[dict[Any, int], int, float, float]:
    import mtkahypar

    initializer = _mtkahypar_initializer()
    preset_type = _mtkahypar_preset(preset)
    path = Path(_TMPDIR.name) / (
        graph_id.replace("/", "__").replace(" ", "_") + f"__{preset}.metis"
    )
    if not path.exists():
        _write_metis_graph(graph, path)
    context = initializer.context_from_preset(preset_type)
    context.set_partitioning_parameters(
        int(k),
        0.0,
        mtkahypar.Objective.CUT,
    )
    lower = graph.number_of_nodes() // k
    upper = (graph.number_of_nodes() + k - 1) // k
    num_upper = graph.number_of_nodes() - (lower * k)
    target_weights = [upper] * num_upper + [lower] * (k - num_upper)
    context.set_individual_target_block_weights(target_weights)
    loaded = initializer.graph_from_file(
        str(path),
        context,
        mtkahypar.FileFormat.METIS,
    )
    mtkahypar.set_seed(int(seed))
    started = time.perf_counter()
    partitioned = loaded.partition(context)
    runtime = time.perf_counter() - started
    membership = [int(block) for block in partitioned.get_partition()]
    partition = {
        node: block
        for node, block in zip(graph.nodes(), membership)
    }
    edge_cut, balance = _partition_metrics(graph, partition, k)
    return partition, edge_cut, balance, runtime



def _run_native_isolated(
    graph: nx.Graph,
    *,
    strategy: str,
    context: str,
    graph_id: str,
    seed: int,
    k: int,
) -> tuple[dict[Any, int], int, float, float]:
    started = time.perf_counter()
    with tempfile.NamedTemporaryFile(
        prefix="atof-native-",
        suffix=".pkl",
        delete=False,
    ) as handle:
        input_path = Path(handle.name)
        pickle.dump(graph, handle, protocol=pickle.HIGHEST_PROTOCOL)

    try:
        command = [
            sys.executable,
            "-m",
            "atof.native_backend_worker",
            "--strategy",
            strategy,
            "--context",
            context,
            "--graph",
            str(input_path),
            "--graph-id",
            graph_id,
            "--seed",
            str(seed),
            "--k",
            str(k),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
        )
        if completed.returncode != 0:
            detail = completed.stderr[-2000:] or completed.stdout[-2000:]
            raise RuntimeError(
                f"{strategy} isolated worker exited {completed.returncode}: {detail}"
            )

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError(
                f"{strategy} isolated worker returned no JSON payload"
            )
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{strategy} isolated worker returned invalid JSON"
            ) from exc

        nodes = list(graph.nodes())
        membership = payload.get("membership")
        if not isinstance(membership, list) or len(membership) != len(nodes):
            raise RuntimeError(
                f"{strategy} isolated worker returned invalid membership length"
            )
        partition = {
            node: int(block)
            for node, block in zip(nodes, membership)
        }
        edge_cut, balance = _partition_metrics(graph, partition, k)
        return partition, edge_cut, balance, time.perf_counter() - started
    finally:
        input_path.unlink(missing_ok=True)


def run_kaminpar(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    context_name: str = "default",
) -> tuple[dict[Any, int], int, float, float]:
    return _run_native_isolated(
        graph,
        strategy="kaminpar",
        context=context_name,
        graph_id=graph_id,
        seed=seed,
        k=k,
    )


def run_mtkahypar(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    preset: str = "default",
) -> tuple[dict[Any, int], int, float, float]:
    return _run_native_isolated(
        graph,
        strategy="mtkahypar",
        context=preset,
        graph_id=graph_id,
        seed=seed,
        k=k,
    )
