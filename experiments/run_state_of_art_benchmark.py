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
from typing import Callable

import networkx as nx

from atof.strategies import BLOCReloc
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora
from experiments.run_kahip_validation import kahip_balanced_partition
from experiments.run_metis_validation import metis_balanced_partition

SEEDS = (42, 101, 2024)
ITERATIONS = 25
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
HYBRID_PROBE_SAMPLES = 20
HYBRID_WITNESS_PATIENCE = 2

CORE_STRATEGIES = (
    "bloc_reloc_baseline",
    "bloc_reloc_affinity",
    "bloc_reloc_hybrid_fixed",
    "bloc_reloc_adaptive",
    "kernighan_lin",
    "metis",
    "kahip",
    "kaminpar_default",
    "kaminpar_strong",
)


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _edge_cut(graph: nx.Graph, partition: dict) -> int:
    return sum(partition[u] != partition[v] for u, v in graph.edges())



def _balance_error(graph: nx.Graph, partition: dict, k: int) -> float:
    counts = [0] * k
    for block in partition.values():
        counts[int(block)] += 1
    n = graph.number_of_nodes()
    ideal = n / k
    return max(abs(count - ideal) for count in counts) / ideal if ideal else 0.0

def _run_atof(
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    variant: str,
    hybrid_policy: str | None = None,
) -> dict:
    started = time.perf_counter()
    kwargs = {}
    if hybrid_policy is not None:
        kwargs = {
            "hybrid_period": HYBRID_PERIOD,
            "hybrid_samples": HYBRID_SAMPLES,
            "hybrid_policy": hybrid_policy,
            "hybrid_probe_samples": HYBRID_PROBE_SAMPLES,
            "hybrid_witness_patience": HYBRID_WITNESS_PATIENCE,
        }
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


def _run_kernighan_lin(graph: nx.Graph, *, seed: int, k: int) -> dict:
    if k != 2:
        raise ValueError("NetworkX Kernighan-Lin is only defined here for k=2")
    from networkx.algorithms.community import kernighan_lin_bisection

    started = time.perf_counter()
    left, right = kernighan_lin_bisection(
        graph,
        partition=None,
        max_iter=ITERATIONS,
        weight=None,
        seed=seed,
    )
    left = set(left)
    partition = {node: (0 if node in left else 1) for node in graph}
    return {
        "edge_cut": _edge_cut(graph, partition),
        "balance_error": abs(len(left) - len(right)) / graph.number_of_nodes(),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {},
    }


def _run_external(
    runner: Callable[[nx.Graph, int], dict],
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
) -> dict:
    del k
    started = time.perf_counter()
    payload = runner(graph, seed)
    return {
        "edge_cut": int(payload["edge_cut"]),
        "balance_error": float(payload["balance_error"]),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {},
    }


def _strategy_run(
    strategy: str,
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
    graph_id: str,
) -> dict:
    if strategy == "bloc_reloc_baseline":
        return _run_atof(graph, seed=seed, k=k, variant="baseline")
    if strategy == "bloc_reloc_affinity":
        return _run_atof(graph, seed=seed, k=k, variant="affinity")
    if strategy == "bloc_reloc_hybrid_fixed":
        return _run_atof(
            graph,
            seed=seed,
            k=k,
            variant="baseline",
            hybrid_policy="fixed",
        )
    if strategy == "bloc_reloc_adaptive":
        return _run_atof(
            graph,
            seed=seed,
            k=k,
            variant="baseline",
            hybrid_policy="adaptive",
        )
    if strategy == "kernighan_lin":
        return _run_kernighan_lin(graph, seed=seed, k=k)
    if strategy == "metis":
        return _run_external(metis_balanced_partition, graph, seed=seed, k=k)
    if strategy == "kahip":
        return _run_external(kahip_balanced_partition, graph, seed=seed, k=k)
    if strategy == "kaminpar_default":
        return _run_kaminpar(
            graph, graph_id=graph_id, seed=seed, k=k, context_name="default"
        )
    if strategy == "kaminpar_strong":
        return _run_kaminpar(
            graph, graph_id=graph_id, seed=seed, k=k, context_name="strong"
        )
    raise ValueError(f"unknown strategy: {strategy}")



_KAMINPAR_GRAPH_CACHE: dict[str, object] = {}
_KAMINPAR_TMPDIR = tempfile.TemporaryDirectory(prefix="atof-kaminpar-")
_KAMINPAR_INSTANCE_CACHE: dict[str, object] = {}


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    """Write the repository's unweighted undirected graph as METIS format."""
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(
            (index[neighbor] for neighbor in graph.neighbors(node))
        )
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


def _kaminpar_partition(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    context_name: str,
) -> dict:
    import kaminpar

    loaded = _kaminpar_graph(graph, graph_id)
    context_factory = {
        "default": kaminpar.default_context,
        "strong": kaminpar.strong_context,
    }[context_name]

    instance_key = context_name
    instance = _KAMINPAR_INSTANCE_CACHE.get(instance_key)
    if instance is None:
        instance = kaminpar.KaMinPar(num_threads=1, context=context_factory())
        _KAMINPAR_INSTANCE_CACHE[instance_key] = instance

    # KaMinPar exposes a process-level RNG seed; set it immediately before
    # each timed partition call so the seed is explicit and reproducible.
    kaminpar.reseed(int(seed))
    partition = instance.compute_partition(loaded, k=k, eps=0.0)
    return {
        "partition": [int(block) for block in partition],
        "edge_cut": int(kaminpar.edge_cut(loaded, partition)),
    }


def _run_kaminpar(
    graph: nx.Graph,
    *,
    graph_id: str,
    seed: int,
    k: int,
    context_name: str,
) -> dict:
    started = time.perf_counter()
    payload = _kaminpar_partition(
        graph,
        graph_id=graph_id,
        seed=seed,
        k=k,
        context_name=context_name,
    )
    partition = payload["partition"]
    balance = _balance_error(
        graph,
        {node: block for node, block in zip(graph.nodes(), partition)},
        k,
    )
    return {
        "edge_cut": int(payload["edge_cut"]),
        "balance_error": float(balance),
        "runtime_seconds": time.perf_counter() - started,
        "metadata": {
            "context": context_name,
            "seed_control": "kaminpar.reseed",
            "graph_load_in_timing": False,
        },
    }


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _summarize_graph(rows: list[dict], strategies: tuple[str, ...]) -> dict:
    available = {
        strategy: [
            row for row in rows
            if row["strategy"] == strategy and row["status"] == "ok"
        ]
        for strategy in strategies
    }
    means = {
        strategy: {
            "edge_cut": _mean([float(row["edge_cut"]) for row in items]),
            "balance_error": _mean([float(row["balance_error"]) for row in items]),
            "runtime_seconds": _mean([float(row["runtime_seconds"]) for row in items]),
        }
        for strategy, items in available.items()
        if items
    }
    if not means:
        return {"strategies": {}, "best_quality": None}

    best_quality = min(
        means,
        key=lambda name: (means[name]["edge_cut"], means[name]["runtime_seconds"], name),
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
    }


def _aggregate_graph_summaries(
    graph_summaries: dict[str, dict],
    strategies: tuple[str, ...],
) -> dict:
    summary = {}
    for strategy in strategies:
        values = [
            data["strategies"][strategy]["relative_quality_gap"]
            for data in graph_summaries.values()
            if strategy in data["strategies"]
        ]
        runtimes = [
            data["strategies"][strategy]["runtime_ratio_to_graph_median"]
            for data in graph_summaries.values()
            if strategy in data["strategies"]
        ]
        summary[strategy] = {
            "graphs_evaluated": len(values),
            "mean_relative_quality_gap": _mean(values),
            "median_relative_quality_gap": statistics.median(values) if values else 0.0,
            "mean_runtime_ratio_to_graph_median": _mean(runtimes),
        }
    return summary


def run_state_of_art_benchmark(
    output_path: str | Path = "results/state_of_art/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = SEEDS,
    iterations: int = ITERATIONS,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError(
            "The current state-of-art protocol is locked to k=2 so every "
            "core candidate uses the same balanced-bisection contract."
        )
    if not seeds:
        raise ValueError("seeds must not be empty")
    if iterations != ITERATIONS:
        raise ValueError("iterations must remain fixed at 25 for this protocol")

    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    strategies = CORE_STRATEGIES
    rows: list[dict] = []

    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in seeds:
                for strategy in strategies:
                    row = {
                        "corpus": corpus,
                        "graph": graph_name,
                        "graph_id": graph_id,
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                        "seed": seed,
                        "strategy": strategy,
                    }
                    try:
                        result = _strategy_run(
                            strategy,
                            graph,
                            seed=seed,
                            k=k,
                            graph_id=graph_id,
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

    graph_rows: dict[str, list[dict]] = {}
    for row in rows:
        graph_rows.setdefault(row["graph_id"], []).append(row)

    graph_summaries = {
        graph_id: _summarize_graph(group, strategies)
        for graph_id, group in graph_rows.items()
    }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "20-graph head-to-head balanced-bisection benchmark across "
            "ATOF local/hybrid refinements, NetworkX Kernighan-Lin, METIS, "
            "and KaHIP"
        ),
        "unit_of_analysis": "graph",
        "objective": {
            "name": "unweighted edge cut",
            "balance": "balanced 2-way partition",
            "direction": "minimize edge cut",
        },
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "hybrid": {
            "period": HYBRID_PERIOD,
            "samples": HYBRID_SAMPLES,
            "adaptive_probe_samples": HYBRID_PROBE_SAMPLES,
            "adaptive_witness_patience": HYBRID_WITNESS_PATIENCE,
        },
        "candidate_strategies": list(strategies),
        "corpora": {
            corpus: {
                "graph_count": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "rows": rows,
        "graph_summaries": graph_summaries,
        "aggregate": _aggregate_graph_summaries(graph_summaries, strategies),
        "limitations": [
            "This is a balanced-bisection comparison, so it does not replace k-way evaluation.",
            "Runtime values are machine-specific and include Python wrapper overhead.",
            "KaMinPar is identified as a required next reference integration but is not silently approximated by another backend.",
            "No claim of state-of-the-art superiority is made by this benchmark alone.",
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
        default=Path("results/state_of_art/latest.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()

    payload = run_state_of_art_benchmark(
        output_path=args.output,
        cache_dir=args.cache_dir,
    )
    print(json.dumps(payload["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
