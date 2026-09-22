from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from experiments.generate_suite import build_suite
from atof.strategies import BLOCReloc


SEEDS = (42, 101, 2024)
VARIANTS = ("baseline", "affinity")
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
ITERATIONS = 25


def run_ablation() -> dict:
    rows: list[dict] = []
    started = time.perf_counter()

    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                base = BLOCReloc(
                    graph,
                    k=2,
                    seed=seed,
                    variant=variant,
                )
                hybrid = BLOCReloc(
                    graph,
                    k=2,
                    seed=seed,
                    variant=variant,
                )

                base_started = time.perf_counter()
                base_result = base.refine(iterations=ITERATIONS)
                base_runtime = time.perf_counter() - base_started

                hybrid_started = time.perf_counter()
                hybrid_result = hybrid.refine(
                    iterations=ITERATIONS,
                    hybrid_period=HYBRID_PERIOD,
                    hybrid_samples=HYBRID_SAMPLES,
                )
                hybrid_runtime = time.perf_counter() - hybrid_started

                rows.append(
                    {
                        "graph": graph_name,
                        "seed": seed,
                        "variant": variant,
                        "iterations": ITERATIONS,
                        "hybrid_period": HYBRID_PERIOD,
                        "hybrid_samples": HYBRID_SAMPLES,
                        "base_edge_cut": base_result.edge_cut,
                        "hybrid_edge_cut": hybrid_result.edge_cut,
                        "edge_cut_delta": hybrid_result.edge_cut - base_result.edge_cut,
                        "base_weighted_cost": base_result.weighted_cost,
                        "hybrid_weighted_cost": hybrid_result.weighted_cost,
                        "weighted_cost_delta": hybrid_result.weighted_cost - base_result.weighted_cost,
                        "base_balance_error": base_result.balance_error,
                        "hybrid_balance_error": hybrid_result.balance_error,
                        "base_runtime_seconds": base_runtime,
                        "hybrid_runtime_seconds": hybrid_runtime,
                        "hybrid_accepted_moves": hybrid_result.accepted_moves,
                    }
                )

    improved = sum(row["edge_cut_delta"] < 0 for row in rows)
    tied = sum(row["edge_cut_delta"] == 0 for row in rows)
    worsened = sum(row["edge_cut_delta"] > 0 for row in rows)

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "seeds": list(SEEDS),
        "variants": list(VARIANTS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "improved_edge_cut": improved,
            "tied_edge_cut": tied,
            "worsened_edge_cut": worsened,
            "mean_edge_cut_delta": (
                sum(row["edge_cut_delta"] for row in rows) / len(rows)
                if rows
                else 0.0
            ),
            "mean_hybrid_runtime_ratio": (
                sum(
                    row["hybrid_runtime_seconds"] / row["base_runtime_seconds"]
                    for row in rows
                    if row["base_runtime_seconds"] > 0
                )
                / sum(row["base_runtime_seconds"] > 0 for row in rows)
                if rows
                else 0.0
            ),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/hybrid-ablation/latest.json"),
    )
    args = parser.parse_args()

    payload = run_ablation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
