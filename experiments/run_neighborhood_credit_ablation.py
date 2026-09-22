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
CREDIT_CONFIGS = (
    {"threshold": 1.00, "max_skips": 1, "probe_samples": 50},
)


def run_pair(graph, *, seed: int, variant: str, threshold: float, max_skips: int, probe_samples: int, fixed) -> dict:
    credit_started = time.perf_counter()
    credit = BLOCReloc(graph, k=K, seed=seed, variant=variant).refine(
        iterations=ITERATIONS,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
        hybrid_policy="credit",
        hybrid_credit_threshold=threshold,
        hybrid_credit_max_skips=max_skips,
        hybrid_credit_probe_samples=probe_samples,
    )
    credit_runtime = time.perf_counter() - credit_started

    fixed_samples = sum(
        HYBRID_SAMPLES for row in fixed.trace if int(row["hybrid"]) == 1
    )
    credit_samples = sum(
        HYBRID_SAMPLES for row in credit.trace if int(row["hybrid"]) == 1
    )

    return {
        "threshold": threshold,
        "max_skips": max_skips,
        "probe_samples": probe_samples,
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "k_fixed": K,
        "k_credit": K,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "fixed_edge_cut": fixed.edge_cut,
        "credit_edge_cut": credit.edge_cut,
        "edge_cut_delta": credit.edge_cut - fixed.edge_cut,
        "fixed_weighted_cost": fixed.weighted_cost,
        "credit_weighted_cost": credit.weighted_cost,
        "weighted_cost_delta": credit.weighted_cost - fixed.weighted_cost,
        "fixed_runtime_seconds": 0.0,
        "credit_runtime_seconds": credit_runtime,
        "runtime_ratio": None,
        "fixed_hybrid_passes": fixed.hybrid_passes,
        "credit_hybrid_passes": credit.hybrid_passes,
        "pass_delta": credit.hybrid_passes - fixed.hybrid_passes,
        "fixed_samples_used": fixed_samples,
        "credit_samples_used": credit_samples,
        "sample_delta": credit_samples - fixed_samples,
    }


def run_benchmark() -> dict:
    rows: list[dict] = []
    started = time.perf_counter()

    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                fixed_started = time.perf_counter()
                fixed = BLOCReloc(graph, k=K, seed=seed, variant=variant).refine(
                    iterations=ITERATIONS,
                    hybrid_period=HYBRID_PERIOD,
                    hybrid_samples=HYBRID_SAMPLES,
                    hybrid_policy="fixed",
                )
                fixed_runtime = time.perf_counter() - fixed_started

                for config in CREDIT_CONFIGS:
                    row = run_pair(
                        graph,
                        seed=seed,
                        variant=variant,
                        threshold=config["threshold"],
                        max_skips=config["max_skips"],
                        probe_samples=config["probe_samples"],
                        fixed=fixed,
                    )
                    row["fixed_runtime_seconds"] = fixed_runtime
                    row["runtime_ratio"] = (
                        row["credit_runtime_seconds"] / fixed_runtime
                        if fixed_runtime > 0
                        else None
                    )
                    rows.append({"graph": graph_name, **row})

    summaries = []
    for config in CREDIT_CONFIGS:
        subset = [
            row
            for row in rows
            if row["threshold"] == config["threshold"]
            and row["max_skips"] == config["max_skips"]
            and row["probe_samples"] == config["probe_samples"]
        ]
        deltas = [row["edge_cut_delta"] for row in subset]
        ratios = [row["runtime_ratio"] for row in subset if row["runtime_ratio"] is not None]
        summaries.append(
            {
                "threshold": config["threshold"],
                "max_skips": config["max_skips"],
                "probe_samples": config["probe_samples"],
                "comparisons": len(subset),
                "better_edge_cut": sum(delta < 0 for delta in deltas),
                "tied_edge_cut": sum(delta == 0 for delta in deltas),
                "worse_edge_cut": sum(delta > 0 for delta in deltas),
                "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
                "mean_runtime_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
                "mean_pass_delta": (
                    sum(row["pass_delta"] for row in subset) / len(subset)
                    if subset
                    else 0.0
                ),
                "mean_sample_delta": (
                    sum(row["sample_delta"] for row in subset) / len(subset)
                    if subset
                    else 0.0
                ),
            }
        )

    return {
        "schema_version": "0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "surface": "atof.strategies.BLOCReloc",
        "k": K,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "configs": list(CREDIT_CONFIGS),
        "rows": rows,
        "summaries": summaries,
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
    print(json.dumps(payload["summaries"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
