from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.statistics import bootstrap_mean_ci

from experiments.k4_online_selector import (
    RESAMPLES,
    BOOTSTRAP_SEED,
    SEEDS,
    _fit,
    _load,
    _mean,
    _pairwise_medians,
    _predict_alternate,
)

# Fixed before evaluation. No threshold is selected automatically.
THRESHOLDS = (0.0, 0.0025, 0.005, 0.01, 0.02)


def _summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_values = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_values.values())
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_graph_value": _mean(values),
        "bootstrap_95_ci": [lower, upper],
        "graph_values": graph_values,
    }


def _evaluate_threshold(
    records: list[dict],
    threshold: float,
) -> dict:
    top1_by_graph: dict[str, list[float]] = defaultdict(list)
    selector_by_graph: dict[str, list[float]] = defaultdict(list)
    runtime_by_graph: dict[str, list[float]] = defaultdict(list)
    predicted_delta_by_graph: dict[str, list[float]] = defaultdict(list)
    probe_flags: list[int] = []
    action_counts: list[int] = []

    corpora = sorted({str(record["corpus"]) for record in records})

    for heldout in corpora:
        training = [
            record
            for record in records
            if str(record["corpus"]) != heldout
        ]
        test = [
            record
            for record in records
            if str(record["corpus"]) == heldout
        ]

        router = _fit(training)
        pair_median, candidate_median, rank_median = _pairwise_medians(
            training,
            router,
        )

        for record in test:
            ranking = router.rank(record["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            probe = predicted_delta < -threshold
            top1 = ranking[0]

            for seed in SEEDS:
                seed_values = record["by_seed"].get(seed)
                if seed_values is None:
                    seed_values = record["by_seed"][str(seed)]

                oracle_strategy = min(
                    seed_values,
                    key=lambda strategy: (
                        float(seed_values[strategy]["edge_cut"]),
                        strategy,
                    ),
                )
                oracle_cut = float(seed_values[oracle_strategy]["edge_cut"])
                top1_cut = float(seed_values[top1]["edge_cut"])
                alternate_cut = float(seed_values[alternate]["edge_cut"])

                if probe:
                    selected_cut = min(top1_cut, alternate_cut)
                    selected_runtime = (
                        float(seed_values[top1]["runtime_seconds"])
                        + float(seed_values[alternate]["runtime_seconds"])
                    )
                    action_count = 2
                else:
                    selected_cut = top1_cut
                    selected_runtime = float(seed_values[top1]["runtime_seconds"])
                    action_count = 1

                top1_regret = (
                    (top1_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                selector_regret = (
                    (selected_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )

                graph_id = record["graph_id"]
                top1_by_graph[graph_id].append(top1_regret)
                selector_by_graph[graph_id].append(selector_regret)
                runtime_by_graph[graph_id].append(selected_runtime)
                predicted_delta_by_graph[graph_id].append(predicted_delta)
                probe_flags.append(int(probe))
                action_counts.append(action_count)

    graph_ids = sorted(top1_by_graph)
    paired_delta = [
        _mean(selector_by_graph[graph_id]) - _mean(top1_by_graph[graph_id])
        for graph_id in graph_ids
    ]
    lower, upper = bootstrap_mean_ci(
        paired_delta,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    return {
        "threshold": threshold,
        "selector": _summary(selector_by_graph),
        "top1": _summary(top1_by_graph),
        "paired_selector_minus_top1": {
            "mean": _mean(paired_delta),
            "bootstrap_95_ci": [lower, upper],
            "better_graphs": sum(value < 0 for value in paired_delta),
            "worse_graphs": sum(value > 0 for value in paired_delta),
            "ties": sum(value == 0 for value in paired_delta),
        },
        "probe_rate": _mean(probe_flags),
        "mean_actions": _mean(action_counts),
        "mean_runtime_seconds": _mean(
            value
            for graph_values in runtime_by_graph.values()
            for value in graph_values
        ),
        "mean_predicted_relative_delta": _mean(
            value
            for graph_values in predicted_delta_by_graph.values()
            for value in graph_values
        ),
    }


def run(path: Path) -> dict:
    payload, records = _load(path)
    cells = [
        _evaluate_threshold(records, threshold)
        for threshold in THRESHOLDS
    ]

    return {
        "schema_version": "1.0",
        "protocol": (
            "k=4 oracle-free online selector threshold sensitivity "
            "under the frozen five-seed leave-one-corpus-out protocol"
        ),
        "benchmark_commit": payload.get("benchmark_commit") or payload.get("commit_sha"),
        "benchmark_head": payload.get("benchmark_head") or payload.get("git_head_sha"),
        "k": 4,
        "seeds": list(SEEDS),
        "thresholds": list(THRESHOLDS),
        "selection_policy": (
            "Run topology rank-1. Predict the rank-2/rank-3 alternate "
            "from training-only ordered-pair medians. Probe the alternate "
            "only when predicted relative edge-cut delta is below "
            "the negative threshold. Maximum two actions."
        ),
        "cells": cells,
        "evidence_boundary": [
            "Each threshold is evaluated independently inside the same leave-one-corpus-out folds.",
            "Held-out seed outcomes are evaluation-only and never drive the probe decision.",
            "The threshold grid is fixed before evaluation and no cell is selected automatically.",
            "The benchmark candidate set, topology router, seeds, and solver protocol are inherited unchanged from the validated k=4 study.",
            "No production/default ATOF behavior changes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["cells"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
