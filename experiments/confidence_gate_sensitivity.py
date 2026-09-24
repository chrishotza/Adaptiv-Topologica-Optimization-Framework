from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Mapping, Sequence

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from experiments.confidence_gated_allocation import (
    _centroid_margin,
    _load_records,
    _predicted_runtime_per_edge,
    _regret,
)

BUDGET_FACTORS: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)
QUANTILES: tuple[float, ...] = (0.25, 0.50, 0.75)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _threshold(training: list[dict], quantile: float) -> float:
    margins: list[float] = []
    for index, held_out in enumerate(training):
        inner_training = training[:index] + training[index + 1 :]
        if len(inner_training) < 2:
            continue
        router = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(inner_training)
        margin = _centroid_margin(router, held_out["topology"])
        if margin != float("inf"):
            margins.append(margin)
    if not margins:
        return float("inf")
    ordered = sorted(margins)
    position = min(
        len(ordered) - 1,
        max(0, round((len(ordered) - 1) * quantile)),
    )
    return float(ordered[position])


def _evaluate_variant(
    records: list[dict],
    *,
    budget_factor: float,
    quantile: float,
) -> tuple[list[dict], list[dict], dict[str, float]]:
    corpora = sorted({row["corpus"] for row in records})
    candidate: list[dict] = []
    baseline: list[dict] = {}

    rows_candidate: list[dict] = []
    rows_baseline: list[dict] = []

    for test_corpus in corpora:
        training = [row for row in records if row["corpus"] != test_corpus]
        testing = [row for row in records if row["corpus"] == test_corpus]
        if not training or not testing:
            continue

        router = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        threshold = _threshold(training, quantile)
        runtime_per_edge = _predicted_runtime_per_edge(training)

        for row in testing:
            ranked = router.rank(row["topology"])
            first = ranked[0]
            margin = _centroid_margin(router, row["topology"])
            chosen = [first]

            predicted_first = runtime_per_edge[first] * row["edges"]

            if len(ranked) > 1 and margin < threshold:
                second = ranked[1]
                predicted_total = predicted_first + runtime_per_edge[second] * row["edges"]
                if predicted_total <= budget_factor * predicted_first:
                    chosen.append(second)

            selected = min(
                chosen,
                key=lambda strategy: (
                    float(row["strategy_metrics"][strategy]["edge_cut"]),
                    strategy,
                ),
            )
            candidate_row = {
                "graph_id": row["graph_id"],
                "corpus": test_corpus,
                "relative_regret": _regret(row, selected),
                "runtime_seconds": sum(
                    float(row["strategy_metrics"][strategy]["runtime_seconds"])
                    for strategy in chosen
                ),
                "actions": len(chosen),
                "margin": margin,
                "threshold": threshold,
                "selected": selected,
                "oracle": row["oracle_strategy"],
            }
            baseline_row = {
                "graph_id": row["graph_id"],
                "corpus": test_corpus,
                "relative_regret": _regret(row, first),
                "runtime_seconds": float(row["strategy_metrics"][first]["runtime_seconds"]),
                "actions": 1,
                "margin": margin,
                "selected": first,
                "oracle": row["oracle_strategy"],
            }
            rows_candidate.append(candidate_row)
            rows_baseline.append(baseline_row)

    return rows_candidate, rows_baseline, {
        "threshold_quantile": quantile,
        "budget_factor": budget_factor,
    }


def _summarize(candidate: list[dict], baseline: list[dict]) -> dict:
    deltas = [
        float(c["relative_regret"]) - float(b["relative_regret"])
        for c, b in zip(candidate, baseline)
    ]
    runtimes = [float(row["runtime_seconds"]) for row in candidate]
    base_runtimes = [float(row["runtime_seconds"]) for row in baseline]
    ci_low, ci_high = bootstrap_mean_ci(deltas, resamples=20000, seed=2026)
    return {
        "graphs": len(candidate),
        "mean_relative_regret": _mean([float(row["relative_regret"]) for row in candidate]),
        "baseline_mean_relative_regret": _mean(
            [float(row["relative_regret"]) for row in baseline]
        ),
        "mean_delta_regret_candidate_minus_baseline": _mean(deltas),
        "bootstrap_95_ci_delta": [ci_low, ci_high],
        "mean_runtime_seconds": _mean(runtimes),
        "baseline_mean_runtime_seconds": _mean(base_runtimes),
        "runtime_overhead_seconds": _mean(runtimes) - _mean(base_runtimes),
        "probe_rate": _mean([row["actions"] > 1 for row in candidate]),
        "mean_actions": _mean([float(row["actions"]) for row in candidate]),
        "candidate_better_graphs": sum(delta < 0 for delta in deltas),
        "candidate_worse_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
    }


def run_analysis(
    benchmark_path: str | Path,
    output_path: str | Path,
) -> dict:
    benchmark, records = _load_records(Path(benchmark_path))
    matrix: list[dict] = []

    for quantile in QUANTILES:
        for budget_factor in BUDGET_FACTORS:
            candidate, baseline, params = _evaluate_variant(
                records,
                budget_factor=budget_factor,
                quantile=quantile,
            )
            matrix.append({
                **params,
                "summary": _summarize(candidate, baseline),
            })

    payload = {
        "schema_version": "1.0",
        "protocol": "leave-one-corpus-out confidence-gate sensitivity matrix",
        "unit_of_analysis": "graph",
        "source_benchmark": str(benchmark_path),
        "source_commit": benchmark.get("commit_sha"),
        "matched_graphs": len(records),
        "quantiles": list(QUANTILES),
        "budget_factors": list(BUDGET_FACTORS),
        "matrix": matrix,
        "frozen_reference": {
            "budget_factor": 2.0,
            "quantile": 0.50,
        },
        "evidence_boundary": [
            "Every threshold is recomputed from training corpora only.",
            "No held-out outcome influences whether the second strategy is launched.",
            "The matrix is exploratory and reports all tested variants without selecting a production policy.",
            "Public/default ATOF behavior is unchanged.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/confidence_gate_sensitivity_latest.json"),
    )
    args = parser.parse_args()
    payload = run_analysis(args.benchmark, args.output)
    for row in payload["matrix"]:
        print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
