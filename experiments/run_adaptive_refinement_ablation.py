from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from experiments.generate_suite import build_suite
from atof.product import optimize_graph


SEEDS = (42, 101, 2024)
VARIANTS = ("baseline", "affinity")
ITERATIONS = 25
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
HYBRID_PATIENCE = 2
HYBRID_PROBE_SAMPLES = 20


def run_pair(graph, *, seed: int, variant: str) -> dict:
    fixed_started = time.perf_counter()
    fixed = optimize_graph(
        graph,
        k=2,
        seed=seed,
        iterations=ITERATIONS,
        variant=variant,
        hybrid=True,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
        hybrid_policy="fixed",
    )
    fixed_runtime = time.perf_counter() - fixed_started
    fixed_payload = fixed.to_dict(include_partition=False)

    adaptive_started = time.perf_counter()
    adaptive = optimize_graph(
        graph,
        k=2,
        seed=seed,
        iterations=ITERATIONS,
        variant=variant,
        hybrid=True,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
        hybrid_policy="adaptive",
        hybrid_patience=HYBRID_PATIENCE,
        hybrid_probe_samples=HYBRID_PROBE_SAMPLES,
        hybrid_witness_patience=2,
    )
    adaptive_runtime = time.perf_counter() - adaptive_started
    adaptive_payload = adaptive.to_dict(include_partition=False)

    fixed_result = fixed_payload["result"]
    adaptive_result = adaptive_payload["result"]
    fixed_refinement = fixed_payload["strategy"]["hybrid_refinement"]
    adaptive_refinement = adaptive_payload["strategy"]["hybrid_refinement"]

    assert fixed_refinement["policy"] == "fixed"
    assert adaptive_refinement["policy"] == "adaptive"
    assert adaptive_refinement["patience"] == HYBRID_PATIENCE

    return {
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "hybrid_patience": HYBRID_PATIENCE,
        "hybrid_probe_samples": HYBRID_PROBE_SAMPLES,
        "fixed_edge_cut": fixed_result["edge_cut"],
        "adaptive_edge_cut": adaptive_result["edge_cut"],
        "edge_cut_delta": adaptive_result["edge_cut"] - fixed_result["edge_cut"],
        "fixed_weighted_cost": fixed_result["weighted_cost"],
        "adaptive_weighted_cost": adaptive_result["weighted_cost"],
        "weighted_cost_delta": (
            adaptive_result["weighted_cost"] - fixed_result["weighted_cost"]
        ),
        "fixed_runtime_seconds": fixed_runtime,
        "adaptive_runtime_seconds": adaptive_runtime,
        "runtime_ratio": (
            adaptive_runtime / fixed_runtime if fixed_runtime > 0 else None
        ),
        "fixed_passes": fixed_refinement["passes"],
        "adaptive_passes": adaptive_refinement["passes"],
        "adaptive_probes": adaptive_refinement["probes"],
        "pass_delta": adaptive_refinement["passes"] - fixed_refinement["passes"],
        "probe_delta": adaptive_refinement["probes"] - fixed_refinement["probes"],
        "fixed_selected": fixed_payload["strategy"]["selected"],
        "adaptive_selected": adaptive_payload["strategy"]["selected"],
    }


def run_benchmark() -> dict:
    rows: list[dict] = []
    started = time.perf_counter()

    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                rows.append(
                    {
                        "graph": graph_name,
                        **run_pair(graph, seed=seed, variant=variant),
                    }
                )

    deltas = [row["edge_cut_delta"] for row in rows]
    ratios = [row["runtime_ratio"] for row in rows if row["runtime_ratio"] is not None]
    pass_deltas = [row["pass_delta"] for row in rows]
    probe_deltas = [row["probe_delta"] for row in rows]

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "surface": "atof.product.optimize_graph",
        "seeds": list(SEEDS),
        "variants": list(VARIANTS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "hybrid_patience": HYBRID_PATIENCE,
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "adaptive_better_edge_cut": sum(delta < 0 for delta in deltas),
            "tied_edge_cut": sum(delta == 0 for delta in deltas),
            "adaptive_worse_edge_cut": sum(delta > 0 for delta in deltas),
            "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_runtime_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
            "mean_hybrid_pass_delta": (
                sum(pass_deltas) / len(pass_deltas) if pass_deltas else 0.0
            ),
            "mean_probe_delta": (
                sum(probe_deltas) / len(probe_deltas) if probe_deltas else 0.0
            ),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/adaptive-refinement-ablation/latest.json"),
    )
    args = parser.parse_args()

    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
