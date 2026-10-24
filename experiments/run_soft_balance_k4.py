from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from experiments.generate_suite import build_suite
from atof.soft_balance import SoftBalanceReloc
from atof.strategies import BLOCReloc


SEEDS = (42, 101, 2024)
VARIANTS = ("baseline", "affinity")
ITERATIONS = 25
K = 4
BALANCE_SLACK = 1
PENALTIES = (0.25, 0.5, 1.0, 2.0)


def run_benchmark() -> dict:
    rows: list[dict] = []

    for graph_name, graph in build_suite().items():
        for seed in SEEDS:
            for variant in VARIANTS:
                strict = BLOCReloc(graph, k=K, seed=seed, variant=variant).refine(
                    iterations=ITERATIONS,
                    hybrid_period=None,
                )
                for penalty in PENALTIES:
                    soft = SoftBalanceReloc(
                        graph, k=K, seed=seed, variant=variant
                    ).refine(
                        iterations=ITERATIONS,
                        balance_slack=BALANCE_SLACK,
                        balance_penalty=penalty,
                    )
                    rows.append(
                        {
                            "graph": graph_name,
                            "seed": seed,
                            "variant": variant,
                            "penalty": penalty,
                            "k": K,
                            "strict_edge_cut": strict.edge_cut,
                            "soft_edge_cut": soft.edge_cut,
                            "edge_cut_delta": soft.edge_cut - strict.edge_cut,
                            "strict_balance_error": strict.balance_error,
                            "soft_balance_error": soft.balance_error,
                            "temporary_imbalance_steps": sum(
                                float(row["balance_error"]) > 0 for row in soft.trace
                            ),
                        }
                    )

    summaries = []
    for penalty in PENALTIES:
        subset = [row for row in rows if row["penalty"] == penalty]
        deltas = [row["edge_cut_delta"] for row in subset]
        summaries.append(
            {
                "penalty": penalty,
                "comparisons": len(subset),
                "better_edge_cut": sum(delta < 0 for delta in deltas),
                "tied_edge_cut": sum(delta == 0 for delta in deltas),
                "worse_edge_cut": sum(delta > 0 for delta in deltas),
                "mean_edge_cut_delta": sum(deltas) / len(deltas) if deltas else 0.0,
                "balanced_outputs": sum(
                    row["soft_balance_error"] == 0.0 for row in subset
                ),
                "mean_temporary_imbalance_steps": (
                    sum(row["temporary_imbalance_steps"] for row in subset)
                    / len(subset)
                    if subset else 0.0
                ),
            }
        )

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "experiments.generate_suite.build_suite",
        "surface": "atof.soft_balance.SoftBalanceReloc",
        "k": K,
        "balance_slack": BALANCE_SLACK,
        "penalties": list(PENALTIES),
        "rows": rows,
        "summaries": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/soft-balance-k4/latest.json"),
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summaries"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
