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
MAX_SAMPLES = 100
BATCH_SAMPLES = 20
IDLE_PATIENCE = 2


def run_pair(graph, *, seed: int, variant: str) -> dict:
    fixed_started = time.perf_counter()
    fixed = BLOCReloc(graph, k=2, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=MAX_SAMPLES,
        hybrid_policy="fixed",
    )
    fixed_runtime = time.perf_counter() - fixed_started

    early_started = time.perf_counter()
    early = BLOCReloc(graph, k=2, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=MAX_SAMPLES,
        hybrid_policy="early_stop",
        hybrid_batch_samples=BATCH_SAMPLES,
        hybrid_idle_patience=IDLE_PATIENCE,
    )
    early_runtime = time.perf_counter() - early_started

    fixed_samples = sum(int(row["hybrid_samples"]) for row in fixed.trace)
    early_samples = sum(int(row["hybrid_samples"]) for row in early.trace)
    fixed_passes = sum(int(row["hybrid"]) for row in fixed.trace)
    early_passes = sum(int(row["hybrid"]) for row in early.trace)

    return {
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "max_samples": MAX_SAMPLES,
        "batch_samples": BATCH_SAMPLES,
        "idle_patience": IDLE_PATIENCE,
        "fixed_edge_cut": fixed.edge_cut,
        "early_edge_cut": early.edge_cut,
        "edge_cut_delta": early.edge_cut - fixed.edge_cut,
        "fixed_weighted_cost": fixed.weighted_cost,
        "early_weighted_cost": early.weighted_cost,
        "weighted_cost_delta": early.weighted_cost - fixed.weighted_cost,
        "fixed_runtime_seconds": fixed_runtime,
        "early_runtime_seconds": early_runtime,
        "runtime_ratio": early_runtime / fixed_runtime if fixed_runtime > 0 else None,
        "fixed_passes": fixed_passes,
        "early_passes": early_passes,
        "pass_delta": early_passes - fixed_passes,
        "fixed_samples_used": fixed_samples,
        "early_samples_used": early_samples,
        "sample_delta": early_samples - fixed_samples,
        "sample_ratio": early_samples / fixed_samples if fixed_samples > 0 else None,
        "early_batch_history": [
            int(row["hybrid_samples"])
            for row in early.trace
            if int(row["hybrid"]) == 1
        ],
    }


def run_benchmark() -> dict:
    rows: list[dict] = []
    started = time.perf_counter()
    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                rows.append({"graph": graph_name, **run_pair(graph, seed=seed, variant=variant)})

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
        "max_samples": MAX_SAMPLES,
        "batch_samples": BATCH_SAMPLES,
        "idle_patience": IDLE_PATIENCE,
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "early_better_edge_cut": sum(delta < 0 for delta in deltas),
            "tied_edge_cut": sum(delta == 0 for delta in deltas),
            "early_worse_edge_cut": sum(delta > 0 for delta in deltas),
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
        default=Path("results/intra-pass-marginal-stop/latest.json"),
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())