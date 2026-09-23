from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci


DEFAULT_BUDGET_FACTORS = (1.0, 2.0, 3.0)
DEFAULT_MIN_RELATIVE_IMPROVEMENT = 0.01


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _load_records(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict] = []
    for graph_id, summary in sorted(payload["graph_summaries"].items()):
        if not summary.get("matched"):
            continue
        metadata = payload["graph_metadata"][graph_id]
        records.append(
            {
                "graph_id": graph_id,
                "corpus": metadata["corpus"],
                "edges": int(metadata["edges"]),
                "topology": metadata["topology"],
                "oracle_strategy": str(summary["best_quality"]),
                "strategy_metrics": {
                    strategy: {
                        "edge_cut": float(values["edge_cut"]),
                        "runtime_seconds": float(values["runtime_seconds"]),
                    }
                    for strategy, values in summary["strategies"].items()
                },
            }
        )
    if not records:
        raise ValueError("benchmark contains no matched graph summaries")
    return payload, records


def _fixed_strategy(training: list[dict], mode: str) -> str:
    if mode == "majority":
        counts = Counter(row["oracle_strategy"] for row in training)
        return min(counts, key=lambda strategy: (-counts[strategy], strategy))

    if mode == "global_mean":
        values: dict[str, list[float]] = {}
        for row in training:
            for strategy, metrics in row["strategy_metrics"].items():
                values.setdefault(strategy, []).append(float(metrics["edge_cut"]))
        return min(values, key=lambda strategy: (_mean(values[strategy]), strategy))

    raise ValueError(f"unknown control: {mode}")


def _runtime_per_edge(training: list[dict]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in training:
        edges = max(1, int(row["edges"]))
        for strategy, metrics in row["strategy_metrics"].items():
            values.setdefault(strategy, []).append(
                float(metrics["runtime_seconds"]) / edges
            )
    return {
        strategy: statistics.median(costs)
        for strategy, costs in values.items()
    }


def _graph_regret(row: Mapping, selected: str) -> float:
    oracle = float(row["strategy_metrics"][row["oracle_strategy"]]["edge_cut"])
    value = float(row["strategy_metrics"][selected]["edge_cut"])
    return (value - oracle) / oracle if oracle else 0.0


def _run_policy(
    row: dict,
    ranking: tuple[str, ...],
    predicted_cost: Mapping[str, float],
    *,
    budget_factor: float,
    min_relative_improvement: float,
) -> dict:
    if not ranking:
        raise ValueError("ranking must contain at least one strategy")

    first = ranking[0]
    budget = budget_factor * predicted_cost[first]
    predicted_used = 0.0
    observed_best = float("inf")
    chosen: list[str] = []
    stop_reason = "budget_exhausted"

    for strategy in ranking:
        candidate_cost = predicted_cost[strategy]
        if strategy != first and predicted_used + candidate_cost > budget:
            stop_reason = "budget_exhausted"
            break

        predicted_used += candidate_cost
        chosen.append(strategy)
        observed_cut = float(row["strategy_metrics"][strategy]["edge_cut"])

        previous_best = observed_best
        observed_best = min(observed_best, observed_cut)

        if strategy != first and previous_best < float("inf"):
            improvement = (
                previous_best - observed_cut
            ) / previous_best if previous_best else 0.0
            if improvement < min_relative_improvement:
                stop_reason = "no_material_improvement"
                break

    if not chosen:
        raise RuntimeError("policy selected no strategy")

    actual_runtime = sum(
        float(row["strategy_metrics"][strategy]["runtime_seconds"])
        for strategy in chosen
    )
    selected_cut = min(
        float(row["strategy_metrics"][strategy]["edge_cut"])
        for strategy in chosen
    )
    selected_strategy = min(
        chosen,
        key=lambda strategy: (
            float(row["strategy_metrics"][strategy]["edge_cut"]),
            strategy,
        ),
    )

    return {
        "selected_strategy": selected_strategy,
        "selected_edge_cut": selected_cut,
        "relative_regret": _graph_regret(row, selected_strategy),
        "actual_runtime_seconds": actual_runtime,
        "actions": len(chosen),
        "chosen_strategies": chosen,
        "predicted_budget": budget,
        "predicted_cost_used": predicted_used,
        "stop_reason": stop_reason,
    }


def _summarize(rows: list[dict], baseline_key: str = "router") -> dict:
    if not rows:
        return {"graphs": 0}

    regrets = [float(row["relative_regret"]) for row in rows]
    runtimes = [float(row["actual_runtime_seconds"]) for row in rows]
    actions = [int(row["actions"]) for row in rows]
    oracle_agreement = sum(
        row["selected_strategy"] == row["oracle_strategy"] for row in rows
    ) / len(rows)

    return {
        "graphs": len(rows),
        "mean_relative_regret": _mean(regrets),
        "median_relative_regret": statistics.median(regrets),
        "mean_runtime_seconds": _mean(runtimes),
        "mean_actions": _mean(actions),
        "oracle_agreement_rate": oracle_agreement,
        "baseline_key": baseline_key,
    }


def _compare(candidate_rows: list[dict], baseline_rows: list[dict]) -> dict:
    deltas = [
        float(candidate["relative_regret"]) - float(baseline["relative_regret"])
        for candidate, baseline in zip(candidate_rows, baseline_rows)
    ]
    ci_low, ci_high = bootstrap_mean_ci(deltas, resamples=20000, seed=2026)
    return {
        "mean_delta_regret_candidate_minus_baseline": _mean(deltas),
        "bootstrap_95_ci_delta": [ci_low, ci_high],
        "candidate_better_graphs": sum(delta < 0 for delta in deltas),
        "candidate_worse_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
    }


def run_analysis(
    benchmark_path: str | Path,
    output_path: str | Path,
    *,
    budget_factors: tuple[float, ...] = DEFAULT_BUDGET_FACTORS,
    min_relative_improvement: float = DEFAULT_MIN_RELATIVE_IMPROVEMENT,
) -> dict:
    benchmark, records = _load_records(Path(benchmark_path))
    corpora = sorted({row["corpus"] for row in records})
    candidates = list(benchmark["candidate_strategies"])

    folds: dict[str, dict] = {}
    pooled_rows: dict[str, list[dict]] = {}
    comparisons: dict[str, dict] = {}

    for test_corpus in corpora:
        training = [row for row in records if row["corpus"] != test_corpus]
        testing = [row for row in records if row["corpus"] == test_corpus]
        if not training or not testing:
            continue

        router = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        cost_per_edge = _runtime_per_edge(training)
        controls = {
            "majority": _fixed_strategy(training, "majority"),
            "global_mean": _fixed_strategy(training, "global_mean"),
        }

        fold_policy_rows: dict[str, list[dict]] = {}
        baseline_rows: list[dict] = []

        for row in testing:
            ranking = router.rank(row["topology"])
            primary = ranking[0]
            primary_metrics = row["strategy_metrics"][primary]
            base = {
                "graph_id": row["graph_id"],
                "corpus": test_corpus,
                "oracle_strategy": row["oracle_strategy"],
                "selected_strategy": primary,
                "relative_regret": _graph_regret(row, primary),
                "actual_runtime_seconds": float(primary_metrics["runtime_seconds"]),
                "actions": 1,
                "chosen_strategies": [primary],
            }
            baseline_rows.append(base)
            pooled_rows.setdefault("centroid_top1", []).append(base)

            predicted_cost = {
                strategy: max(
                    cost_per_edge[strategy] * max(1, int(row["edges"])),
                    1e-12,
                )
                for strategy in candidates
                if strategy in cost_per_edge
            }

            for budget_factor in budget_factors:
                scenario = f"trajectory_b{budget_factor:g}"
                outcome = _run_policy(
                    row,
                    ranking,
                    predicted_cost,
                    budget_factor=budget_factor,
                    min_relative_improvement=min_relative_improvement,
                )
                outcome.update(
                    {
                        "graph_id": row["graph_id"],
                        "corpus": test_corpus,
                        "oracle_strategy": row["oracle_strategy"],
                    }
                )
                fold_policy_rows.setdefault(scenario, []).append(outcome)
                pooled_rows.setdefault(scenario, []).append(outcome)

            for control_name, strategy in controls.items():
                row_out = {
                    "graph_id": row["graph_id"],
                    "corpus": test_corpus,
                    "oracle_strategy": row["oracle_strategy"],
                    "selected_strategy": strategy,
                    "relative_regret": _graph_regret(row, strategy),
                    "actual_runtime_seconds": float(
                        row["strategy_metrics"][strategy]["runtime_seconds"]
                    ),
                    "actions": 1,
                    "chosen_strategies": [strategy],
                }
                pooled_rows.setdefault(control_name, []).append(row_out)

        fold_summary = {
            "graphs": len(testing),
            "router": "centroid",
            "predicted_runtime_model": "training median runtime per edge",
            "controls": controls,
            "policies": {
                scenario: _summarize(rows, baseline_key="centroid_top1")
                for scenario, rows in fold_policy_rows.items()
            },
            "baseline": _summarize(
                baseline_rows,
                baseline_key="centroid_top1",
            ),
        }
        folds[test_corpus] = fold_summary

    for scenario in pooled_rows:
        if scenario == "centroid_top1":
            continue
        comparisons[f"{scenario}_vs_centroid_top1"] = _compare(
            pooled_rows[scenario],
            pooled_rows["centroid_top1"],
        )

    summaries = {
        key: _summarize(rows, baseline_key="centroid_top1")
        for key, rows in pooled_rows.items()
    }

    payload = {
        "schema_version": "1.0",
        "protocol": (
            "offline replay of trajectory-aware sequential solver allocation "
            "with leave-one-corpus-out topology priors"
        ),
        "unit_of_analysis": "graph",
        "source_benchmark": str(benchmark_path),
        "source_commit": benchmark.get("commit_sha"),
        "candidate_strategies": candidates,
        "matched_graphs": len(records),
        "corpora": corpora,
        "router": {
            "family": "centroid",
            "scale_mode": "iqr",
            "metric": "l2",
        },
        "predicted_cost_model": "training median runtime_seconds / edges",
        "frozen_policy_parameters": {
            "budget_factors": list(budget_factors),
            "min_relative_improvement": min_relative_improvement,
        },
        "folds": folds,
        "pooled_summaries": summaries,
        "paired_comparisons": comparisons,
        "evidence_boundary": [
            "This benchmark is an offline replay over already-measured solver outcomes.",
            "Router fitting, cost estimation, and scaling use training corpora only.",
            "Held-out solver outcomes are treated as observations revealed only when their ranked action is replayed.",
            "Reported runtime is measured test runtime; budget feasibility is decided from training-only predicted cost.",
            "No public/default ATOF behavior is changed by this experiment.",
            "This layer does not claim superiority over external solvers.",
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
        default=Path("results/state_of_art/trajectory_allocation_latest.json"),
    )
    args = parser.parse_args()
    payload = run_analysis(args.benchmark, args.output)
    print(json.dumps(payload["pooled_summaries"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
