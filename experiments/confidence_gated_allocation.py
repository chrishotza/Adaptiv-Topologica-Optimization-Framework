from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Mapping

from atof.routing import LearnedTopologyRouter, topology_vector, _distance
from atof.statistics import bootstrap_mean_ci

BUDGET_FACTOR = 2.0
QUANTILE = 0.50
MIN_IMPROVEMENT = 0.0

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def _load_records(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for graph_id, summary in sorted(payload["graph_summaries"].items()):
        if not summary.get("matched"):
            continue
        metadata = payload["graph_metadata"][graph_id]
        records.append({
            "graph_id": graph_id,
            "corpus": metadata["corpus"],
            "edges": max(1, int(metadata["edges"])),
            "topology": metadata["topology"],
            "oracle_strategy": str(summary["best_quality"]),
            "strategy_metrics": {
                strategy: {
                    "edge_cut": float(values["edge_cut"]),
                    "runtime_seconds": float(values["runtime_seconds"]),
                }
                for strategy, values in summary["strategies"].items()
            },
        })
    if not records:
        raise ValueError("benchmark contains no matched graphs")
    return payload, records

def _centroid_margin(router: LearnedTopologyRouter, topology: Mapping) -> float:
    vector = topology_vector(topology, router.features)
    distances = {
        strategy: _distance(vector, router._centroids[strategy], router._scale, router.metric)
        for strategy in router.strategies
    }
    ranked = sorted(distances, key=lambda strategy: (distances[strategy], strategy))
    if len(ranked) < 2:
        return float("inf")
    first, second = distances[ranked[0]], distances[ranked[1]]
    return (second - first) / first if first else float("inf")

def _inner_margin_threshold(training: list[dict], quantile: float) -> float:
    margins = []
    for index, held_out in enumerate(training):
        inner_training = training[:index] + training[index + 1:]
        if len(inner_training) < 2:
            continue
        router = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(inner_training)
        margin = _centroid_margin(router, held_out["topology"])
        if margin != float("inf"):
            margins.append(margin)
    if not margins:
        return float("inf")
    return float(statistics.quantiles(margins, n=100, method="inclusive")[int(quantile * 100) - 1])

def _predicted_runtime_per_edge(training: list[dict]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in training:
        for strategy, metrics in row["strategy_metrics"].items():
            values.setdefault(strategy, []).append(float(metrics["runtime_seconds"]) / row["edges"])
    return {strategy: statistics.median(samples) for strategy, samples in values.items()}

def _regret(row: Mapping, selected: str) -> float:
    oracle = float(row["strategy_metrics"][row["oracle_strategy"]]["edge_cut"])
    selected_cut = float(row["strategy_metrics"][selected]["edge_cut"])
    return (selected_cut - oracle) / oracle if oracle else 0.0

def run_analysis(
    benchmark_path: str | Path,
    output_path: str | Path,
    *,
    budget_factor: float = BUDGET_FACTOR,
    quantile: float = QUANTILE,
    min_improvement: float = MIN_IMPROVEMENT,
) -> dict:
    benchmark, records = _load_records(Path(benchmark_path))
    if not 0.0 < quantile <= 1.0:
        raise ValueError("quantile must be in (0,1]")
    if budget_factor < 1.0:
        raise ValueError("budget_factor must be >= 1")

    corpora = sorted({row["corpus"] for row in records})
    pooled, baseline, folds = [], [], {}

    for test_corpus in corpora:
        training = [row for row in records if row["corpus"] != test_corpus]
        testing = [row for row in records if row["corpus"] == test_corpus]
        if not training or not testing:
            continue
        router = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        threshold = _inner_margin_threshold(training, quantile)
        runtime_per_edge = _predicted_runtime_per_edge(training)
        fold_rows = []

        for row in testing:
            ranked = router.rank(row["topology"])
            first = ranked[0]
            margin = _centroid_margin(router, row["topology"])
            first_predicted = runtime_per_edge[first] * row["edges"]
            chosen = [first]
            action = "single_shot"

            if len(ranked) > 1 and margin < threshold:
                second = ranked[1]
                predicted_total = first_predicted + runtime_per_edge[second] * row["edges"]
                if predicted_total <= budget_factor * first_predicted:
                    first_cut = float(row["strategy_metrics"][first]["edge_cut"])
                    second_cut = float(row["strategy_metrics"][second]["edge_cut"])
                    observed_improvement = (first_cut - second_cut) / first_cut if first_cut else 0.0
                    if observed_improvement >= min_improvement:
                        chosen.append(second)
                        action = "probe_second"

            selected = min(chosen, key=lambda strategy: (float(row["strategy_metrics"][strategy]["edge_cut"]), strategy))
            actual_runtime = sum(float(row["strategy_metrics"][strategy]["runtime_seconds"]) for strategy in chosen)
            result = {
                "graph_id": row["graph_id"],
                "corpus": test_corpus,
                "oracle_strategy": row["oracle_strategy"],
                "selected_strategy": selected,
                "ranked_strategies": list(ranked[:3]),
                "confidence_margin": margin,
                "training_margin_threshold": threshold,
                "action": action,
                "actions": len(chosen),
                "chosen_strategies": chosen,
                "relative_regret": _regret(row, selected),
                "actual_runtime_seconds": actual_runtime,
            }
            pooled.append(result)
            fold_rows.append(result)

            baseline.append({
                "graph_id": row["graph_id"],
                "corpus": test_corpus,
                "oracle_strategy": row["oracle_strategy"],
                "selected_strategy": first,
                "confidence_margin": margin,
                "action": "single_shot",
                "actions": 1,
                "chosen_strategies": [first],
                "relative_regret": _regret(row, first),
                "actual_runtime_seconds": float(row["strategy_metrics"][first]["runtime_seconds"]),
            })

        folds[test_corpus] = {
            "graphs": len(fold_rows),
            "threshold": threshold,
            "summary": {
                "mean_relative_regret": _mean([row["relative_regret"] for row in fold_rows]),
                "mean_runtime_seconds": _mean([row["actual_runtime_seconds"] for row in fold_rows]),
                "probe_second_rate": _mean([row["actions"] > 1 for row in fold_rows]),
            },
        }

    deltas = [candidate["relative_regret"] - base["relative_regret"] for candidate, base in zip(pooled, baseline)]
    ci_low, ci_high = bootstrap_mean_ci(deltas, resamples=20000, seed=2026)
    payload = {
        "schema_version": "1.0",
        "protocol": "leave-one-corpus-out confidence-gated two-stage solver allocation",
        "unit_of_analysis": "graph",
        "source_benchmark": str(benchmark_path),
        "source_commit": benchmark.get("commit_sha"),
        "matched_graphs": len(records),
        "corpora": corpora,
        "router": {"family": "centroid", "scale_mode": "iqr", "metric": "l2"},
        "frozen_policy": {
            "budget_factor": budget_factor,
            "confidence_quantile": quantile,
            "min_improvement_after_probe": min_improvement,
            "threshold_is_training_only": True,
        },
        "folds": folds,
        "summary": {
            "mean_relative_regret": _mean([row["relative_regret"] for row in pooled]),
            "mean_runtime_seconds": _mean([row["actual_runtime_seconds"] for row in pooled]),
            "probe_second_rate": _mean([row["actions"] > 1 for row in pooled]),
            "mean_actions": _mean([row["actions"] for row in pooled]),
        },
        "baseline_summary": {
            "mean_relative_regret": _mean([row["relative_regret"] for row in baseline]),
            "mean_runtime_seconds": _mean([row["actual_runtime_seconds"] for row in baseline]),
        },
        "paired_comparison": {
            "mean_delta_regret_candidate_minus_baseline": _mean(deltas),
            "bootstrap_95_ci_delta": [ci_low, ci_high],
            "candidate_better_graphs": sum(delta < 0 for delta in deltas),
            "candidate_worse_graphs": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
        },
        "evidence_boundary": [
            "Confidence thresholds are computed from training corpora only.",
            "No held-out oracle label is used to decide whether to probe the second strategy.",
            "The second strategy is selected from the topology-only centroid ranking.",
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
    parser.add_argument("--output", type=Path, default=Path("results/state_of_art/confidence_gated_allocation_latest.json"))
    args = parser.parse_args()
    payload = run_analysis(args.benchmark, args.output)
    print(json.dumps(payload["summary"], indent=2))
    print(json.dumps(payload["baseline_summary"], indent=2))
    print(json.dumps(payload["paired_comparison"], indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
