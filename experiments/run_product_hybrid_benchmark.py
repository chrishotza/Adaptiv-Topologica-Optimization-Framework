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


def run_pair(graph, *, seed: int, variant: str) -> dict:
    base_started = time.perf_counter()
    base = optimize_graph(
        graph,
        k=2,
        seed=seed,
        iterations=ITERATIONS,
        variant=variant,
        hybrid=False,
    )
    base_runtime = time.perf_counter() - base_started
    base_payload = base.to_dict(include_partition=False)

    hybrid_started = time.perf_counter()
    hybrid = optimize_graph(
        graph,
        k=2,
        seed=seed,
        iterations=ITERATIONS,
        variant=variant,
        hybrid=True,
        hybrid_period=HYBRID_PERIOD,
        hybrid_samples=HYBRID_SAMPLES,
    )
    hybrid_runtime = time.perf_counter() - hybrid_started
    hybrid_payload = hybrid.to_dict(include_partition=False)

    base_result = base_payload["result"]
    hybrid_result = hybrid_payload["result"]
    base_strategy = base_payload["strategy"]["hybrid_refinement"]
    hybrid_strategy = hybrid_payload["strategy"]["hybrid_refinement"]

    assert base_strategy == {
        "enabled": False,
        "policy": "off",
        "period": None,
        "samples": HYBRID_SAMPLES,
        "patience": 2,
        "probe_samples": 20,
        "passes": 0,
        "probes": 0,
    }
    assert hybrid_strategy == {
        "enabled": True,
        "policy": "fixed",
        "period": HYBRID_PERIOD,
        "samples": HYBRID_SAMPLES,
        "patience": 2,
        "probe_samples": 20,
        "passes": ITERATIONS // HYBRID_PERIOD,
        "probes": 0,
    }

    return {
        "seed": seed,
        "variant": variant,
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "base_edge_cut": base_result["edge_cut"],
        "hybrid_edge_cut": hybrid_result["edge_cut"],
        "edge_cut_delta": hybrid_result["edge_cut"] - base_result["edge_cut"],
        "base_weighted_cost": base_result["weighted_cost"],
        "hybrid_weighted_cost": hybrid_result["weighted_cost"],
        "weighted_cost_delta": (
            hybrid_result["weighted_cost"] - base_result["weighted_cost"]
        ),
        "base_balance_error": base_result["balance_error"],
        "hybrid_balance_error": hybrid_result["balance_error"],
        "base_runtime_seconds": base_runtime,
        "hybrid_runtime_seconds": hybrid_runtime,
        "runtime_ratio": (
            hybrid_runtime / base_runtime if base_runtime > 0 else None
        ),
        "selected_variant_base": base_payload["strategy"]["selected"],
        "selected_variant_hybrid": hybrid_payload["strategy"]["selected"],
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
        "rows": rows,
        "summary": {
            "comparisons": len(rows),
            "improved_edge_cut": sum(delta < 0 for delta in deltas),
            "tied_edge_cut": sum(delta == 0 for delta in deltas),
            "worsened_edge_cut": sum(delta > 0 for delta in deltas),
            "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_runtime_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/product-hybrid-benchmark/latest.json"),
    )
    args = parser.parse_args()

    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
