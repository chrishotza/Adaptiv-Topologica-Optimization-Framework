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
HYBRID_SAMPLES = 100
K = 3


def run_pair(graph, *, seed: int, variant: str) -> dict:
    fixed_started = time.perf_counter()
    fixed = BLOCReloc(graph, k=K, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
        hybrid_policy="fixed",
    )
    fixed_runtime = time.perf_counter() - fixed_started

    credit_started = time.perf_counter()
    credit = BLOCReloc(graph, k=2, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
        hybrid_policy="credit",
    )
    credit_runtime = time.perf_counter() - credit_started

    fixed_samples = sum(
        HYBRID_SAMPLES for row in fixed.trace if int(row["hybrid"]) == 1
    )
    credit_samples = sum(
        HYBRID_SAMPLES for row in credit.trace if int(row["hybrid"]) == 1
    )

    return {
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "k": K,
        "hybrid_samples": HYBRID_SAMPLES,
        "fixed_edge_cut": fixed.edge_cut,
        "credit_edge_cut": credit.edge_cut,
        "edge_cut_delta": credit.edge_cut - fixed.edge_cut,
        "fixed_weighted_cost": fixed.weighted_cost,
        "credit_weighted_cost": credit.weighted_cost,
        "weighted_cost_delta": credit.weighted_cost - fixed.weighted_cost,
        "fixed_runtime_seconds": fixed_runtime,
        "credit_runtime_seconds": credit_runtime,
        "runtime_ratio": credit_runtime / fixed_runtime if fixed_runtime > 0 else None,
        "fixed_hybrid_passes": fixed.hybrid_passes,
        "credit_hybrid_passes": credit.hybrid_passes,
        "pass_delta": credit.hybrid_passes - fixed.hybrid_passes,
        "fixed_samples_used": fixed_samples,
        "credit_samples_used": credit_samples,
        "sample_delta": credit_samples - fixed_samples,
        "credit_trace": [
            {
                "iteration": int(row["iteration"]),
                "hybrid": int(row["hybrid"]),
                "local_credit": float(row["local_credit"]),
                "hybrid_credit": float(row["hybrid_credit"]),
                "local_work": int(row["local_work"]),
                "hybrid_work": int(row["hybrid_work"]),
            }
            for row in credit.trace
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

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "surface": "atof.strategies.BLOCReloc",
        "seeds": list(SEEDS),
        "variants": list(VARIANTS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "k": K,
        "hybrid_samples": HYBRID_SAMPLES,
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "credit_better_edge_cut": sum(delta < 0 for delta in deltas),
            "tied_edge_cut": sum(delta == 0 for delta in deltas),
            "credit_worse_edge_cut": sum(delta > 0 for delta in deltas),
            "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_runtime_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
            "mean_pass_delta": (
                sum(row["pass_delta"] for row in rows) / len(rows) if rows else 0.0
            ),
            "mean_sample_delta": (
                sum(row["sample_delta"] for row in rows) / len(rows) if rows else 0.0
            ),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/neighborhood-credit-ablation/latest.json"),
    )
    args = parser.parse_args()

    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
