from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import networkx as nx

from atof.adaptive import build_regime_signature_v2
from atof.native_backends import run_kaminpar, run_mtkahypar
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora
from experiments.run_kahip_validation import kahip_balanced_partition
from experiments.run_metis_validation import metis_balanced_partition

SEEDS = (42, 101, 2024)
ITERATIONS = 25

STRATEGIES = (
    "bloc_reloc_baseline",
    "bloc_reloc_affinity",
    "bloc_reloc_hybrid_fixed",
    "bloc_reloc_adaptive",
    "kernighan_lin",
    "metis",
    "kahip",
    "kaminpar_default",
    "kaminpar_strong",
    "mtkahypar_default",
    "mtkahypar_quality",
)

LOCAL_STRATEGIES = STRATEGIES[:5]
ISOLATED_STRATEGIES = STRATEGIES[5:]


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
    target = graph.number_of_nodes() / k
    return max(abs(count - target) for count in counts) / target if target else 0.0


def _result(edge_cut: int, balance_error: float, runtime: float, **metadata) -> dict:
    return {
        "edge_cut": int(edge_cut),
        "balance_error": float(balance_error),
        "runtime_seconds": float(runtime),
        "metadata": metadata,
    }


def _run_local(
    strategy: str,
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
) -> dict:
    if strategy == "kernighan_lin":
        if k != 2:
            raise ValueError("Kernighan-Lin is only defined here for k=2")
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
        return _result(
            _edge_cut(graph, partition),
            abs(len(left) - len(right)) / graph.number_of_nodes(),
            time.perf_counter() - started,
        )

    variant = "baseline" if strategy != "bloc_reloc_affinity" else "affinity"
    hybrid_policy = {
        "bloc_reloc_hybrid_fixed": "fixed",
        "bloc_reloc_adaptive": "adaptive",
    }.get(strategy)

    started = time.perf_counter()
    result = BLOCReloc(
        graph,
        k=k,
        seed=seed,
        variant=variant,
    ).refine(
        iterations=ITERATIONS,
        hybrid_period=5 if hybrid_policy else None,
        hybrid_samples=100 if hybrid_policy else 0,
        hybrid_policy=hybrid_policy or "fixed",
        hybrid_probe_samples=20 if hybrid_policy else 0,
        hybrid_witness_patience=2 if hybrid_policy else 2,
    )
    return _result(
        result.edge_cut,
        result.balance_error,
        time.perf_counter() - started,
        hybrid_passes=int(result.hybrid_passes),
        hybrid_probes=int(result.hybrid_probes),
    )


def run_strategy(
    strategy: str,
    graph: nx.Graph,
    *,
    seed: int,
    k: int,
) -> dict:
    if strategy in LOCAL_STRATEGIES:
        return _run_local(strategy, graph, seed=seed, k=k)

    if strategy == "metis":
        started = time.perf_counter()
        payload = metis_balanced_partition(graph, seed=seed)
        return _result(
            payload["edge_cut"],
            payload["balance_error"],
            time.perf_counter() - started,
            backend="metis",
        )

    if strategy == "kahip":
        started = time.perf_counter()
        payload = kahip_balanced_partition(graph, seed=seed)
        return _result(
            payload["edge_cut"],
            payload["balance_error"],
            time.perf_counter() - started,
            backend="kahip",
        )

    if strategy == "kaminpar_default":
        started = time.perf_counter()
        partition, cut, balance = run_kaminpar(
            graph,
            seed=seed,
            k=k,
            quality=False,
        )
        return _result(
            cut,
            balance,
            time.perf_counter() - started,
            backend="kaminpar",
            context="default",
        )

    if strategy == "kaminpar_strong":
        started = time.perf_counter()
        partition, cut, balance = run_kaminpar(
            graph,
            seed=seed,
            k=k,
            quality=True,
        )
        return _result(
            cut,
            balance,
            time.perf_counter() - started,
            backend="kaminpar",
            context="strong",
        )

    if strategy == "mtkahypar_default":
        started = time.perf_counter()
        partition, cut, balance = run_mtkahypar(
            graph,
            seed=seed,
            k=k,
            quality=False,
        )
        return _result(
            cut,
            balance,
            time.perf_counter() - started,
            backend="mtkahypar",
            context="default",
        )

    if strategy == "mtkahypar_quality":
        started = time.perf_counter()
        partition, cut, balance = run_mtkahypar(
            graph,
            seed=seed,
            k=k,
            quality=True,
        )
        return _result(
            cut,
            balance,
            time.perf_counter() - started,
            backend="mtkahypar",
            context="quality",
        )

    raise ValueError(f"unknown strategy: {strategy}")


def build_local_rows(
    corpora: dict[str, dict[str, nx.Graph]],
    *,
    seeds: tuple[int, ...],
    k: int,
) -> list[dict]:
    rows: list[dict] = []
    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in seeds:
                for strategy in LOCAL_STRATEGIES:
                    base = {
                        "corpus": corpus,
                        "graph": graph_name,
                        "graph_id": graph_id,
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                        "seed": seed,
                        "strategy": strategy,
                    }
                    try:
                        rows.append({
                            **base,
                            **run_strategy(strategy, graph, seed=seed, k=k),
                            "status": "ok",
                        })
                    except Exception as exc:
                        rows.append({
                            **base,
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
    return rows


def run_isolated_strategy(
    strategy: str,
    *,
    cache_dir: str | Path | None,
) -> list[dict]:
    corpora, _ = _load_expanded_corpora(
        cache_dir=Path(cache_dir) if cache_dir else None
    )
    rows: list[dict] = []
    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in SEEDS:
                base = {
                    "corpus": corpus,
                    "graph": graph_name,
                    "graph_id": graph_id,
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "seed": seed,
                    "strategy": strategy,
                }
                try:
                    rows.append({
                        **base,
                        **run_strategy(strategy, graph, seed=seed, k=2),
                        "status": "ok",
                    })
                except Exception as exc:
                    rows.append({
                        **base,
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
    return rows


def _decode_worker_rows(stdout: str) -> list[dict]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError("worker returned no JSON payload")
    payload = json.loads(lines[-1])
    if not isinstance(payload, list):
        raise ValueError("worker payload must be a list")
    return payload


def _graph_summary(
    graph_rows: list[dict],
    *,
    expected_strategies: tuple[str, ...],
    expected_seeds: tuple[int, ...],
) -> dict:
    ok = [row for row in graph_rows if row.get("status") == "ok"]
    means = {}
    for strategy in expected_strategies:
        values = [
            float(row["edge_cut"])
            for row in ok
            if row["strategy"] == strategy
        ]
        runtimes = [
            float(row["runtime_seconds"])
            for row in ok
            if row["strategy"] == strategy
        ]
        if values:
            means[strategy] = {
                "edge_cut": statistics.fmean(values),
                "balance_error": statistics.fmean(
                    float(row["balance_error"])
                    for row in ok
                    if row["strategy"] == strategy
                ),
                "runtime_seconds": statistics.fmean(runtimes),
            }

    complete = True
    incomplete = {}
    expected_seed_set = set(expected_seeds)
    for strategy in expected_strategies:
        observed = {
            int(row["seed"])
            for row in ok
            if row["strategy"] == strategy
        }
        if observed != expected_seed_set:
            complete = False
            incomplete[strategy] = sorted(observed)

    if not complete or len(means) != len(expected_strategies):
        return {
            "matched": False,
            "strategies": means,
            "expected_seeds": list(expected_seeds),
            "observed_seeds": incomplete,
        }

    best = min(
        means,
        key=lambda strategy: (
            means[strategy]["edge_cut"],
            means[strategy]["runtime_seconds"],
            strategy,
        ),
    )
    best_cut = means[best]["edge_cut"]
    for metrics in means.values():
        metrics["relative_quality_gap"] = (
            (metrics["edge_cut"] - best_cut) / best_cut
            if best_cut
            else 0.0
        )
    return {
        "matched": True,
        "strategies": means,
        "best_quality": best,
        "best_edge_cut": best_cut,
    }


def _load_topology_metadata(
    corpora: dict[str, dict[str, nx.Graph]],
) -> dict[str, dict]:
    profiler = TopologyProfiler()
    metadata = {}
    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            profile = profiler.profile(graph)
            metadata[graph_id] = {
                "corpus": corpus,
                "graph": graph_name,
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "topology": profile.to_dict(),
                "regime_signature": build_regime_signature_v2(
                    graph,
                    k=2,
                    profile=profile,
                ).to_dict(),
            }
    return metadata


def run_benchmark(
    output_path: str | Path,
    *,
    seeds: tuple[int, ...] = SEEDS,
    cache_dir: str | Path | None = None,
) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(
        cache_dir=Path(cache_dir) if cache_dir else None
    )
    rows = build_local_rows(corpora, seeds=seeds, k=2)

    for strategy in ISOLATED_STRATEGIES:
        command = [
            sys.executable,
            "-m",
            "experiments.fresh_sota_protocol",
            "--worker",
            "--strategy",
            strategy,
        ]
        if cache_dir is not None:
            command.extend(["--cache-dir", str(cache_dir)])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        if completed.returncode == 0:
            rows.extend(_decode_worker_rows(completed.stdout))
        else:
            error = (
                f"worker exit {completed.returncode}"
                + (f": {completed.stderr[-1200:]}" if completed.stderr else "")
            )
            for corpus, graphs in corpora.items():
                for graph_name, graph in graphs.items():
                    for seed in seeds:
                        rows.append({
                            "corpus": corpus,
                            "graph": graph_name,
                            "graph_id": f"{corpus}/{graph_name}",
                            "nodes": graph.number_of_nodes(),
                            "edges": graph.number_of_edges(),
                            "seed": seed,
                            "strategy": strategy,
                            "status": "worker_error",
                            "error": error,
                        })

    graph_metadata = _load_topology_metadata(corpora)
    graph_summaries = {}
    for graph_id in sorted(graph_metadata):
        graph_rows = [row for row in rows if row["graph_id"] == graph_id]
        graph_summaries[graph_id] = _graph_summary(
            graph_rows,
            expected_strategies=STRATEGIES,
            expected_seeds=seeds,
        )

    matched = [
        item
        for item in graph_summaries.values()
        if item.get("matched")
    ]

    payload = {
        "schema_version": "1.0",
        "protocol": "fresh 20-graph k=2 SOTA head-to-head",
        "unit_of_analysis": "graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": 2,
        "seeds": list(seeds),
        "iterations": ITERATIONS,
        "candidate_strategies": list(STRATEGIES),
        "local_strategies": list(LOCAL_STRATEGIES),
        "isolated_strategies": list(ISOLATED_STRATEGIES),
        "corpora": {
            corpus: {
                "graph_count": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "graph_metadata": graph_metadata,
        "rows": rows,
        "graph_summaries": graph_summaries,
        "matched_graphs": len(matched),
        "runtime_seconds": time.perf_counter() - started,
        "evidence_boundary": [
            "This is a fresh confirmatory benchmark using the current main-branch ATOF integration.",
            "External native backends run in isolated Python worker processes.",
            "No router or controller is trained from test-graph solver outcomes in this benchmark.",
            "The benchmark measures endpoint quality, balance, and runtime; it does not claim that ATOF itself outperforms the external solvers.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/state_of_art/fresh_latest.json"))
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--strategy", choices=ISOLATED_STRATEGIES)
    args = parser.parse_args()

    if args.worker:
        if not args.strategy:
            raise SystemExit("--strategy is required with --worker")
        rows = run_isolated_strategy(args.strategy, cache_dir=args.cache_dir)
        print(json.dumps(rows, separators=(",", ":")))
        return 0

    payload = run_benchmark(args.output, cache_dir=args.cache_dir)
    print(json.dumps({
        "matched_graphs": payload["matched_graphs"],
        "total_rows": len(payload["rows"]),
        "strategies": payload["candidate_strategies"],
    }, indent=2))
    return 0
