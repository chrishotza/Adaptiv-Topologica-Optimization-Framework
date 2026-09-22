from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

from atof.routing import LearnedTopologyRouter, NearestTopologyRouter
from atof.statistics import bootstrap_mean_ci


ROUTERS = ("nearest", "centroid")
CONTROLS = ("majority", "global_mean")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _exact_sign_flip_p_one_sided(values: list[float]) -> float:
    if not values:
        return 1.0
    observed = _mean(values)
    n = len(values)
    total = 1 << n
    count = 0
    for mask in range(total):
        signed_sum = 0.0
        for i, value in enumerate(values):
            signed_sum += value if (mask >> i) & 1 else -value
        if signed_sum / n <= observed + 1e-15:
            count += 1
    return count / total


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _load_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    graph_summaries = payload["graph_summaries"]
    metadata = payload["graph_metadata"]
    records = []

    for graph_id, summary in sorted(graph_summaries.items()):
        if not summary.get("matched"):
            continue
        item = metadata[graph_id]
        strategy_means = {
            name: float(values["edge_cut"])
            for name, values in summary["strategies"].items()
        }
        if len(strategy_means) != len(payload["candidate_strategies"]):
            continue
        corpus, graph_name = graph_id.split("/", 1)
        records.append(
            {
                "graph_id": graph_id,
                "corpus": corpus,
                "graph": graph_name,
                "topology": item["topology"],
                "oracle_strategy": str(summary["best_quality"]),
                "strategy_means": strategy_means,
            }
        )

    return records


def _global_mean_strategy(training: list[dict]) -> str:
    strategy_values: dict[str, list[float]] = {}
    for record in training:
        for strategy, value in record["strategy_means"].items():
            strategy_values.setdefault(strategy, []).append(value)
    return min(
        strategy_values,
        key=lambda strategy: (_mean(strategy_values[strategy]), strategy),
    )


def _majority_strategy(training: list[dict]) -> str:
    counts = Counter(record["oracle_strategy"] for record in training)
    return min(counts, key=lambda strategy: (-counts[strategy], strategy))


def _regret(record: dict, selected: str) -> float:
    oracle_value = float(record["strategy_means"][record["oracle_strategy"]])
    selected_value = float(record["strategy_means"][selected])
    return (
        (selected_value - oracle_value) / oracle_value
        if oracle_value
        else 0.0
    )


def _summarize(rows: list[dict], router: str, control: str) -> dict:
    subset = [
        row for row in rows
        if row["router"] == router and row["control"] == control
    ]
    deltas = [
        float(row["router_relative_regret"]) - float(row["control_relative_regret"])
        for row in subset
    ]
    lower, upper = bootstrap_mean_ci(
        deltas,
        resamples=20000,
        seed=2026,
    )
    return {
        "graphs": len(subset),
        "mean_router_relative_regret": _mean(
            [float(row["router_relative_regret"]) for row in subset]
        ),
        "mean_control_relative_regret": _mean(
            [float(row["control_relative_regret"]) for row in subset]
        ),
        "mean_delta_router_minus_control": _mean(deltas),
        "bootstrap_95_ci": [lower, upper],
        "exact_sign_flip_p_one_sided": _exact_sign_flip_p_one_sided(deltas),
        "router_better_graphs": sum(delta < 0 for delta in deltas),
        "router_worse_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
    }


def run_analysis(
    benchmark_path: str | Path = "results/state_of_art/latest.json",
    output_path: str | Path = "results/state_of_art/solver_router_transfer.json",
) -> dict:
    benchmark = Path(benchmark_path)
    records = _load_records(benchmark)
    if len(records) < 2:
        raise ValueError("not enough matched graph records for transfer analysis")

    corpora = sorted({record["corpus"] for record in records})
    folds: dict[str, list[dict]] = {}

    for test_corpus in corpora:
        training = [
            record for record in records if record["corpus"] != test_corpus
        ]
        testing = [
            record for record in records if record["corpus"] == test_corpus
        ]
        if not training or not testing:
            continue

        nearest = NearestTopologyRouter(
            scale_mode="iqr",
            metric="l2",
        ).fit(training)
        centroid = LearnedTopologyRouter(
            scale_mode="iqr",
            metric="l2",
        ).fit(training)
        controls = {
            "majority": _majority_strategy(training),
            "global_mean": _global_mean_strategy(training),
        }

        fold_rows: list[dict] = []
        for record in testing:
            predictions = {
                "nearest": nearest.predict(record["topology"]),
                "centroid": centroid.predict(record["topology"]),
            }
            for router, selected in predictions.items():
                for control, control_strategy in controls.items():
                    fold_rows.append(
                        {
                            "test_corpus": test_corpus,
                            "graph_id": record["graph_id"],
                            "oracle_strategy": record["oracle_strategy"],
                            "router": router,
                            "router_strategy": selected,
                            "control": control,
                            "control_strategy": control_strategy,
                            "router_relative_regret": _regret(record, selected),
                            "control_relative_regret": _regret(record, control_strategy),
                        }
                    )
        folds[test_corpus] = fold_rows

    all_rows = [row for rows in folds.values() for row in rows]
    macro = {
        f"{router}_vs_{control}": _summarize(
            all_rows,
            router,
            control,
        )
        for router in ROUTERS
        for control in CONTROLS
    }
    micro_by_key = {}
    for router in ROUTERS:
        for control in CONTROLS:
            subset = [
                row for row in all_rows
                if row["router"] == router and row["control"] == control
            ]
            micro_by_key[f"{router}_vs_{control}"] = {
                "graphs": len(subset),
                "mean_router_relative_regret": _mean(
                    [float(row["router_relative_regret"]) for row in subset]
                ),
                "mean_control_relative_regret": _mean(
                    [float(row["control_relative_regret"]) for row in subset]
                ),
                "mean_delta_router_minus_control": _mean(
                    [
                        float(row["router_relative_regret"])
                        - float(row["control_relative_regret"])
                        for row in subset
                    ]
                ),
            }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "leave-one-corpus-out topology routing on the fresh 11-strategy "
            "state-of-art benchmark artifact"
        ),
        "unit_of_analysis": "graph",
        "objective": {
            "name": "unweighted edge cut",
            "direction": "minimize edge cut",
            "balance": "matched benchmark contract",
        },
        "router_configs": {
            "nearest": {"features": "all", "scale_mode": "iqr", "metric": "l2"},
            "centroid": {"features": "all", "scale_mode": "iqr", "metric": "l2"},
        },
        "controls": CONTROLS,
        "corpora": corpora,
        "matched_graphs": len(records),
        "rows": all_rows,
        "folds": folds,
        "macro": macro,
        "micro": micro_by_key,
        "source_benchmark": str(benchmark),
        "source_commit": json.loads(
            benchmark.read_text(encoding="utf-8")
        ).get("commit_sha"),
        "python": sys.version,
        "platform": platform.platform(),
        "notes": [
            "Training uses graph-level oracle labels only.",
            "The entire test corpus is excluded from router fitting and feature scaling.",
            "Seeds are already aggregated within the source benchmark at graph level.",
            "The router is evaluated against fixed majority and fixed global-mean controls.",
            "This is a fresh confirmatory transfer analysis, not a tuned public routing policy.",
        ],
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/solver_router_transfer.json"),
    )
    args = parser.parse_args()
    result = run_analysis(args.benchmark, args.output)
    print(json.dumps(result["macro"], indent=2))
