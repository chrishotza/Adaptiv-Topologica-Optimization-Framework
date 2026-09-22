from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from importlib import metadata as importlib_metadata

import networkx as nx

from atof.portfolio import _run_kahip, _run_metis
from atof.strategies import BLOCReloc
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora
from experiments.mtkahypar_backend import run_mtkahypar

SEEDS = (42, 101, 2024)
ITERATIONS = 25
K_VALUES = (4, 8, 32, 64)
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
HYBRID_PROBE_SAMPLES = 20
HYBRID_WITNESS_PATIENCE = 2

STRATEGIES = (
    "bloc_reloc_baseline",
    "bloc_reloc_affinity",
    "bloc_reloc_hybrid_fixed",
    "bloc_reloc_adaptive",
    "metis",
    "kahip",
    "kaminpar_default",
    "kaminpar_strong",
    "mtkahypar_default",
    "mtkahypar_quality",
)

_KAMINPAR_GRAPH_CACHE: dict[str, object] = {}
_KAMINPAR_INSTANCE_CACHE: dict[str, object] = {}
_KAMINPAR_TMPDIR = tempfile.TemporaryDirectory(prefix="atof-kaminpar-kway-")


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for distribution in (
        "atof",
        "networkx",
        "pymetis",
        "kahip",
        "kaminpar",
        "mtkahypar",
    ):
        try:
            versions[distribution] = importlib_metadata.version(distribution)
        except importlib_metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _edge_cut(graph: nx.Graph, partition: dict) -> int:
    return sum(partition[u] != partition[v] for u, v in graph.edges())


def _balance_error(graph: nx.Graph, partition: dict, k: int) -> float:
    counts = [0] * k
    for block in partition.values():
        counts[int(block)] += 1
    n = graph.number_of_nodes()
    ideal = n / k
    return max(abs(count - ideal) for count in counts) / ideal if ideal else 0.0


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(index[neighbor] for neighbor in graph.neighbors(node))
        lines.append(" ".join(str(value) for value in neighbors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _kaminpar_graph(graph: nx.Graph, graph_id: str):
    import kaminpar

    cached = _KAMINPAR_GRAPH_CACHE.get(graph_id)
    if cached is not None:
        return cached

    path = Path(_KAMINPAR_TMPDIR.name) / (
        graph_id.replace("/", "__").replace(" ", "_") + ".metis"
    )
    _write_metis_graph(graph, path)
    loaded = kaminpar.load_graph(
        str(path),
        kaminpar.GraphFileFormat.METIS,
        compress=False,
    )
    _KAMINPAR_GRAPH_CACHE[graph_id] = loaded
    return loaded


def _kaminpar_eps(graph: nx.Graph, k: int) -> float:
    del graph, k
    # KaMinPar's bound is (1 + eps) * ceil(total_weight / k).
    # eps=0 therefore permits exactly floor/ceil block sizes for unit weights.
    return 0.0

def _kaminpar_instance(context_name: str):
    import kaminpar

    factory = {
        "default": kaminpar.default_context,
        "strong": kaminpar.strong_context,
    }[context_name]
    instance = _KAMINPAR_INSTANCE_CACHE.get(context_name)
    if instance is None:
        instance = kaminpar.KaMinPar(1, factory())
        _KAMINPAR_INSTANCE_CACHE[context_name] = instance
    return instance


def _run_kaminpar(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    context_name: str,
) -> dict:
    import kaminpar

    _kaminpar_graph(graph, graph_id)
    _kaminpar_instance(context_name)
    started = time.perf_counter()
    loaded = _kaminpar_graph(graph, graph_id)
    kaminpar.reseed(int(seed))
    partition = _kaminpar_instance(context_name).compute_partition(
        loaded,
        k=k,
        eps=_kaminpar_eps(graph, k),
    )
    partition_map = {
        node: int(block)
        for node, block in zip(graph.nodes(), partition)
    }
    return {
        "edge_cut": int(kaminpar.edge_cut(loaded, partition)),
        "balance_error": _balance_error(graph, partition_map, k),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {
            "context": context_name,
            "seed_control": "kaminpar.reseed",
            "epsilon": _kaminpar_eps(graph, k),
            "graph_load_in_timing": False,
            "backend_init_in_timing": False,
        },
    }


def _run_bloc(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    variant: str,
    policy: str | None = None,
) -> dict:
    kwargs = {}
    if policy is not None:
        kwargs = {
            "hybrid_period": HYBRID_PERIOD,
            "hybrid_samples": HYBRID_SAMPLES,
            "hybrid_policy": policy,
            "hybrid_probe_samples": HYBRID_PROBE_SAMPLES,
            "hybrid_witness_patience": HYBRID_WITNESS_PATIENCE,
        }
    started = time.perf_counter()
    result = BLOCReloc(
        graph,
        k=k,
        seed=seed,
        variant=variant,
    ).refine(iterations=ITERATIONS, **kwargs)
    return {
        "edge_cut": int(result.edge_cut),
        "balance_error": float(result.balance_error),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {
            "hybrid_passes": int(result.hybrid_passes),
            "hybrid_probes": int(result.hybrid_probes),
        },
    }


def _run_external(
    runner,
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
) -> dict:
    started = time.perf_counter()
    partition, edge_cut, balance = runner(
        graph,
        seed=seed,
        k=k,
    )
    return {
        "edge_cut": int(edge_cut),
        "balance_error": float(balance),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {},
    }


def _strategy_run(
    strategy: str,
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
) -> dict:
    if strategy == "bloc_reloc_baseline":
        return _run_bloc(graph, seed=seed, k=k, variant="baseline")
    if strategy == "bloc_reloc_affinity":
        return _run_bloc(graph, seed=seed, k=k, variant="affinity")
    if strategy == "bloc_reloc_hybrid_fixed":
        return _run_bloc(
            graph,
            seed=seed,
            k=k,
            variant="baseline",
            policy="fixed",
        )
    if strategy == "bloc_reloc_adaptive":
        return _run_bloc(
            graph,
            seed=seed,
            k=k,
            variant="baseline",
            policy="adaptive",
        )
    if strategy == "metis":
        return _run_external(_run_metis, graph, seed=seed, k=k)
    if strategy == "kahip":
        return _run_external(_run_kahip, graph, seed=seed, k=k)
    if strategy == "kaminpar_default":
        return _run_kaminpar(
            graph,
            graph_id=graph_id,
            seed=seed,
            k=k,
            context_name="default",
        )
    if strategy == "kaminpar_strong":
        return _run_kaminpar(
            graph,
            graph_id=graph_id,
            seed=seed,
            k=k,
            context_name="strong",
        )
    if strategy == "mtkahypar_default":
        return run_mtkahypar(
            graph,
            graph_id=graph_id,
            seed=seed,
            k=k,
            preset="default",
            epsilon=_kaminpar_eps(graph, k),
        )
    if strategy == "mtkahypar_quality":
        return run_mtkahypar(
            graph,
            graph_id=graph_id,
            seed=seed,
            k=k,
            preset="quality",
            epsilon=_kaminpar_eps(graph, k),
        )
    raise ValueError(f"unknown strategy: {strategy}")


def _summarize_graph(
    rows: list[dict],
    strategies: tuple[str, ...],
) -> dict:
    available = {
        strategy: [
            row for row in rows
            if row["strategy"] == strategy and row["status"] == "ok"
        ]
        for strategy in strategies
    }
    means = {
        strategy: {
            "edge_cut": _mean([float(row["edge_cut"]) for row in values]),
            "balance_error": _mean([float(row["balance_error"]) for row in values]),
            "runtime_seconds": _mean([float(row["runtime_seconds"]) for row in values]),
        }
        for strategy, values in available.items()
        if len(values) > 0
    }
    if not means:
        return {"strategies": {}, "best_quality": None, "matched": False}

    if len(means) != len(strategies):
        return {
            "strategies": means,
            "best_quality": None,
            "matched": False,
        }

    best_quality = min(
        means,
        key=lambda name: (means[name]["edge_cut"], name),
    )
    best_edge_cut = means[best_quality]["edge_cut"]
    median_runtime = statistics.median(
        value["runtime_seconds"] for value in means.values()
    )
    for metrics in means.values():
        metrics["relative_quality_gap"] = (
            (metrics["edge_cut"] - best_edge_cut) / best_edge_cut
            if best_edge_cut
            else 0.0
        )
        metrics["runtime_ratio_to_graph_median"] = (
            metrics["runtime_seconds"] / median_runtime
            if median_runtime
            else 0.0
        )
    return {
        "strategies": means,
        "best_quality": best_quality,
        "best_edge_cut": best_edge_cut,
        "matched": True,
    }


def _aggregate(
    graph_summaries: dict[str, dict],
    strategies: tuple[str, ...],
) -> dict:
    matched = {
        graph_id: summary
        for graph_id, summary in graph_summaries.items()
        if summary.get("matched")
    }
    output = {"matched_graphs": len(matched), "strategies": {}}
    for strategy in strategies:
        gaps = [
            summary["strategies"][strategy]["relative_quality_gap"]
            for summary in matched.values()
        ]
        runtimes = [
            summary["strategies"][strategy]["runtime_ratio_to_graph_median"]
            for summary in matched.values()
        ]
        output["strategies"][strategy] = {
            "graphs": len(gaps),
            "mean_relative_quality_gap": _mean(gaps),
            "median_relative_quality_gap": statistics.median(gaps) if gaps else 0.0,
            "mean_runtime_ratio_to_graph_median": _mean(runtimes),
        }
    return output


def run_kway_state_of_art_benchmark(
    output_path: str | Path = "results/state_of_art/kway_latest.json",
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    rows: list[dict] = []

    for k in K_VALUES:
        for corpus, graphs in corpora.items():
            for graph_name, graph in graphs.items():
                graph_id = f"{corpus}/{graph_name}"
                for seed in SEEDS:
                    for strategy in STRATEGIES:
                        row = {
                            "k": k,
                            "corpus": corpus,
                            "graph": graph_name,
                            "graph_id": graph_id,
                            "nodes": graph.number_of_nodes(),
                            "edges": graph.number_of_edges(),
                            "seed": seed,
                            "strategy": strategy,
                        }
                        if graph.number_of_nodes() < k:
                            row.update(
                                {
                                    "status": "skipped",
                                    "error": "k exceeds graph node count",
                                }
                            )
                            rows.append(row)
                            continue
                        try:
                            result = _strategy_run(
                                strategy,
                                graph,
                                graph_id=graph_id,
                                seed=seed,
                                k=k,
                            )
                            row.update(result)
                            row["status"] = "ok"
                        except Exception as exc:
                            row.update(
                                {
                                    "status": "error",
                                    "error": f"{type(exc).__name__}: {exc}",
                                }
                            )
                        rows.append(row)

    graph_summaries: dict[str, dict] = {}
    for k in K_VALUES:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            if row["k"] != k:
                continue
            grouped.setdefault(row["graph_id"], []).append(row)
        graph_summaries.update(
            {
                f"k={k}:{graph_id}": _summarize_graph(values, STRATEGIES)
                for graph_id, values in grouped.items()
            }
        )

    aggregate = {
        f"k={k}": _aggregate(
            {
                graph_id: summary
                for graph_id, summary in graph_summaries.items()
                if graph_id.startswith(f"k={k}:")
            },
            STRATEGIES,
        )
        for k in K_VALUES
    }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "matched k-way benchmark aligned to the k={4,8,32,64} structure "
            "of SEA 2026, using ATOF's exact floor/ceil balance contract"
        ),
        "objective": {
            "name": "unweighted edge cut",
            "direction": "minimize edge cut",
            "balance": "exact floor/ceil block sizes",
        },
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "package_versions": _package_versions(),
        "seeds": list(SEEDS),
        "iterations": ITERATIONS,
        "k_values": list(K_VALUES),
        "candidate_strategies": list(STRATEGIES),
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "rows": rows,
        "graph_summaries": graph_summaries,
        "aggregate": aggregate,
        "limitations": [
            "The current corpus contains 20 graphs rather than the 118-graph SEA Set A.",
            "NetworkX Kernighan-Lin is excluded because this k-way gate targets candidates that support all requested k values.",
            "SEA 2026 uses epsilon=0.03; ATOF uses exact floor/ceil balance here. A separate reproduction mode is required before comparing published numerical results directly.",
            "Runtime is single-process and machine-specific; the current ATOF research benchmark does not claim parity with the 64-thread SEA 2026 hardware setup.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/kway_latest.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    payload = run_kway_state_of_art_benchmark(
        output_path=args.output,
        cache_dir=args.cache_dir,
    )
    print(json.dumps(payload["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
