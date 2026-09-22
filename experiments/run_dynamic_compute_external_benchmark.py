from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from atof.statistics import paired_summary
from atof.strategies import BLOCReloc
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora


SEEDS = (42, 101, 2024)
ITERATIONS = 25
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
POLICIES = ("off", "fixed", "adaptive", "marginal")


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _run_policy(graph, *, seed: int, policy: str) -> dict:
    kwargs = {
        "iterations": ITERATIONS,
    }
    if policy != "off":
        kwargs.update(
            {
                "hybrid_period": HYBRID_PERIOD,
                "hybrid_samples": HYBRID_SAMPLES,
                "hybrid_policy": policy,
                "hybrid_probe_samples": 20,
                "hybrid_witness_patience": 2,
            }
        )

    started = time.perf_counter()
    result = BLOCReloc(
        graph,
        k=2,
        seed=seed,
        variant="baseline",
    ).refine(**kwargs)
    wall_runtime = time.perf_counter() - started
    total_work = sum(int(event["total_work"]) for event in result.trace)
    probe_work = sum(int(event["probe_work"]) for event in result.trace)

    return {
        "edge_cut": int(result.edge_cut),
        "balance_error": float(result.balance_error),
        "total_work": int(total_work),
        "probe_work": int(probe_work),
        "hybrid_passes": int(result.hybrid_passes),
        "hybrid_probes": int(result.hybrid_probes),
        "runtime_seconds": wall_runtime,
    }


def _policy_summary(rows: list[dict], policy: str) -> dict:
    selected = [row for row in rows if row["strategy"] == policy]
    graph_count = len({row["graph_id"] for row in selected})
    return {
        "graphs": graph_count,
        "rows": len(selected),
        "mean_edge_cut": (
            sum(float(row["edge_cut"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_total_work": (
            sum(float(row["total_work"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_runtime_seconds": (
            sum(float(row["runtime_seconds"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_hybrid_passes": (
            sum(float(row["hybrid_passes"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_probe_work": (
            sum(float(row["probe_work"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
    }


def _dominance_vs_fixed(rows: list[dict], policy: str) -> dict:
    fixed = {
        row["graph_id"]: row
        for row in rows
        if row["strategy"] == "fixed"
    }
    candidate = {
        row["graph_id"]: row
        for row in rows
        if row["strategy"] == policy
    }
    graphs = sorted(set(fixed) & set(candidate))
    dominated = []
    quality_better = []
    work_lower = []
    for graph_id in graphs:
        f = fixed[graph_id]
        c = candidate[graph_id]
        quality_ok = float(c["edge_cut"]) <= float(f["edge_cut"])
        work_ok = float(c["total_work"]) <= float(f["total_work"])
        strict = (
            float(c["edge_cut"]) < float(f["edge_cut"])
            or float(c["total_work"]) < float(f["total_work"])
        )
        if quality_ok and float(c["edge_cut"]) < float(f["edge_cut"]):
            quality_better.append(graph_id)
        if work_ok and float(c["total_work"]) < float(f["total_work"]):
            work_lower.append(graph_id)
        if quality_ok and work_ok and strict:
            dominated.append(graph_id)

    return {
        "graphs": len(graphs),
        "dominates_fixed": len(dominated),
        "quality_strictly_better": len(quality_better),
        "work_strictly_lower": len(work_lower),
        "dominance_rate": len(dominated) / len(graphs) if graphs else 0.0,
    }


def run_benchmark(
    output_path: str | Path = "results/state_of_art/dynamic_compute_external.json",
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    rows: list[dict] = []

    graph_count = sum(len(graphs) for graphs in corpora.values())
    if graph_count != 20:
        raise ValueError(f"expected 20 graphs, discovered {graph_count}")

    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in SEEDS:
                for policy in POLICIES:
                    result = _run_policy(
                        graph,
                        seed=seed,
                        policy=policy,
                    )
                    rows.append(
                        {
                            "corpus": corpus,
                            "graph": graph_name,
                            "graph_id": graph_id,
                            "seed": seed,
                            "strategy": policy,
                            **result,
                        }
                    )

    summaries = {
        policy: _policy_summary(rows, policy)
        for policy in POLICIES
    }

    comparisons = {}
    for policy in ("adaptive", "marginal"):
        comparisons[policy] = {
            "edge_cut_vs_fixed": paired_summary(
                rows,
                strategy_a=policy,
                strategy_b="fixed",
                metric="edge_cut",
                resamples=20000,
                seed=2024,
            ),
            "total_work_vs_fixed": paired_summary(
                rows,
                strategy_a=policy,
                strategy_b="fixed",
                metric="total_work",
                resamples=20000,
                seed=2025,
            ),
            "dominance_vs_fixed": _dominance_vs_fixed(rows, policy),
        }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "20-graph external dynamic-compute ablation for BLOC-RELOC "
            "with fixed, adaptive, marginal, and no-hybrid controls"
        ),
        "unit_of_analysis": "graph",
        "objective": {
            "name": "unweighted edge cut",
            "direction": "minimize edge cut",
            "balance": "exact floor/ceil balanced bisection",
        },
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": 2,
        "seeds": list(SEEDS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "policies": list(POLICIES),
        "corpora": {
            corpus: {
                "graph_count": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "rows": rows,
        "summaries": summaries,
        "comparisons": comparisons,
        "limitations": [
            "This is a BLOC-RELOC controller study, not a comparison against the external multilevel solvers.",
            "Structural work is a machine-independent proxy; wall-clock time remains hardware-specific.",
            "The fixed controller is the primary paired baseline for adaptive and marginal allocation.",
            "No public/default routing policy is changed by this experiment.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/dynamic_compute_external.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run_benchmark(output_path=args.output, cache_dir=args.cache_dir)
    print(json.dumps(result["comparisons"], indent=2))
