from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from experiments.generate_suite import build_suite
from atof.strategies import BLOCReloc


SEEDS = (42, 101, 2024)
VARIANTS = ("baseline", "affinity")
ITERATIONS = 25
HYBRID_PERIOD = 5
INITIAL_SAMPLES = 100
MIN_SAMPLES = 25
MAX_SAMPLES = 200


def run_pair(graph, *, seed: int, variant: str) -> dict:
    fixed_started = time.perf_counter()
    fixed = BLOCReloc(graph, k=2, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=INITIAL_SAMPLES,
    )
    fixed_runtime = time.perf_counter() - fixed_started

    budgeted_started = time.perf_counter()
    budgeted = BLOCReloc(graph, k=2, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=INITIAL_SAMPLES,
        hybrid_policy="budgeted",
    )
    budgeted_runtime = time.perf_counter() - budgeted_started

    fixed_samples = sum(int(row["hybrid_samples"]) for row in fixed.trace)
    budgeted_samples = sum(int(row["hybrid_samples"]) for row in budgeted.trace)
    fixed_passes = sum(int(row["hybrid"]) for row in fixed.trace)
    budgeted_passes = sum(int(row["hybrid"]) for row in budgeted.trace)

    return {
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "initial_samples": INITIAL_SAMPLES,
        "min_samples": MIN_SAMPLES,
        "max_samples": MAX_SAMPLES,
        "fixed_edge_cut": fixed.edge_cut,
        "budgeted_edge_cut": budgeted.edge_cut,
        "edge_cut_delta": budgeted.edge_cut - fixed.edge_cut,
        "fixed_weighted_cost": fixed.weighted_cost,
        "budgeted_weighted_cost": budgeted.weighted_cost,
        "weighted_cost_delta": budgeted.weighted_cost - fixed.weighted_cost,
        "fixed_runtime_seconds": fixed_runtime,
        "budgeted_runtime_seconds": budgeted_runtime,
        "runtime_ratio": budgeted_runtime / fixed_runtime if fixed_runtime > 0 else None,
        "fixed_passes": fixed_passes,
        "budgeted_passes": budgeted_passes,
        "pass_delta": budgeted_passes - fixed_passes,
        "fixed_samples_used": fixed_samples,
        "budgeted_samples_used": budgeted_samples,
        "sample_delta": budgeted_samples - fixed_samples,
        "sample_ratio": budgeted_samples / fixed_samples if fixed_samples > 0 else None,
        "budget_history": [
            int(row["hybrid_samples"])
            for row in budgeted.trace
            if int(row["hybrid"]) == 1
        ],
    }


def run_benchmark() -> dict:
    rows: list[dict] = []
    started = time.perf_counter()
    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                rows.append(
                    {"graph": graph_name, **run_pair(graph, seed=seed, variant=variant)}
                )

    deltas = [row["edge_cut_delta"] for row in rows]
    ratios = [row["runtime_ratio"] for row in rows if row["runtime_ratio"] is not None]
    sample_ratios = [row["sample_ratio"] for row in rows if row["sample_ratio"] is not None]

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "surface": "atof.strategies.BLOCReloc",
        "seeds": list(SEEDS),
        "variants": list(VARIANTS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "initial_samples": INITIAL_SAMPLES,
        "min_samples": MIN_SAMPLES,
        "max_samples": MAX_SAMPLES,
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "budgeted_better_edge_cut": sum(delta < 0 for delta in deltas),
            "tied_edge_cut": sum(delta == 0 for delta in deltas),
            "budgeted_worse_edge_cut": sum(delta > 0 for delta in deltas),
            "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_runtime_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
            "mean_sample_ratio": sum(sample_ratios) / len(sample_ratios) if sample_ratios else 0.0,
            "mean_sample_delta": sum(row["sample_delta"] for row in rows) / len(rows) if rows else 0.0,
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/marginal-budget-ablation/latest.json"),
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())