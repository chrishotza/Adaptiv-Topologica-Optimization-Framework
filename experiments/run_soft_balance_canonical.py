from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from atof.soft_balance import SoftBalanceReloc
from atof.strategies import BLOCReloc


SEEDS = (42, 101, 2024)
VARIANTS = ("baseline", "affinity")
ITERATIONS = 25
K = 2
BALANCE_SLACK = 1
PENALTIES = (0.25, 0.5, 1.0, 2.0)


def run_benchmark() -> dict:
    graph = nx.karate_club_graph()
    rows: list[dict] = []

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
                        "seed": seed,
                        "variant": variant,
                        "penalty": penalty,
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                        "strict_edge_cut": strict.edge_cut,
                        "soft_edge_cut": soft.edge_cut,
                        "edge_cut_delta": soft.edge_cut - strict.edge_cut,
                        "strict_weighted_cost": strict.weighted_cost,
                        "soft_weighted_cost": soft.weighted_cost,
                        "weighted_cost_delta": soft.weighted_cost - strict.weighted_cost,
                        "strict_balance_error": strict.balance_error,
                        "soft_balance_error": soft.balance_error,
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
            }
        )

    return {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "networkx.karate_club_graph",
        "surface": "atof.soft_balance.SoftBalanceReloc",
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
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
        default=Path("results/soft-balance-canonical/latest.json"),
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summaries"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
