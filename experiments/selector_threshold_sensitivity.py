from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from experiments.online_topk_selector import (
    ALTERNATE_RANKS,
    _build_records,
    _fit,
    _load,
    _mean,
    _predict_alternate,
)

THRESHOLDS = (0.0, 0.0025, 0.005, 0.01, 0.02)
RESAMPLES = 5000
BOOTSTRAP_SEED = 2024


def _summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_means = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_means.values())
    if not values:
        return {
            "graphs": 0,
            "mean_graph_value": None,
            "bootstrap_95_ci": None,
        }
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_graph_value": _mean(values),
        "bootstrap_95_ci": [lower, upper],
    }


def _training_predictor(training: list[dict], router) -> tuple[dict, dict, dict]:
    pair_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    candidate_values: dict[str, list[float]] = defaultdict(list)
    rank_values: dict[int, list[float]] = defaultdict(list)

    for item in training:
        ranking = router.rank(item["topology"])
        if len(ranking) < 3:
            continue
        for candidates in item["by_seed"].values():
            top1 = ranking[0]
            top1_cut = candidates[top1]["edge_cut"]
            if top1_cut <= 0:
                continue
            for rank in ALTERNATE_RANKS:
                candidate = ranking[rank]
                delta = (candidates[candidate]["edge_cut"] - top1_cut) / top1_cut
                pair_values[(top1, candidate)].append(delta)
                candidate_values[candidate].append(delta)
                rank_values[rank].append(delta)

    def median(values: list[float]) -> float:
        ordered = sorted(values)
        mid = len(ordered) // 2
        return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0

    return (
        {key: median(values) for key, values in pair_values.items()},
        {key: median(values) for key, values in candidate_values.items()},
        {key: median(values) for key, values in rank_values.items()},
    )


def _evaluate_threshold(
    records: list[dict],
    heldout_corpora: list[str],
    threshold: float,
) -> dict:
    top1_by_graph: dict[str, list[float]] = defaultdict(list)
    selector_by_graph: dict[str, list[float]] = defaultdict(list)
    runtime_by_graph: dict[str, list[float]] = defaultdict(list)
    probes: list[int] = []
    actions: list[int] = []

    for heldout in heldout_corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)
        pair_median, candidate_median, rank_median = _training_predictor(training, router)

        for item in test:
            ranking = router.rank(item["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            probe = predicted_delta < -threshold

            for candidates in item["by_seed"].values():
                oracle = min(
                    candidates,
                    key=lambda name: (candidates[name]["edge_cut"], name),
                )
                oracle_cut = candidates[oracle]["edge_cut"]
                top1 = ranking[0]
                top1_cut = candidates[top1]["edge_cut"]

                if probe:
                    selected_cut = min(top1_cut, candidates[alternate]["edge_cut"])
                    runtime = (
                        candidates[top1]["runtime_seconds"]
                        + candidates[alternate]["runtime_seconds"]
                    )
                    action_count = 2
                else:
                    selected_cut = top1_cut
                    runtime = candidates[top1]["runtime_seconds"]
                    action_count = 1

                top1_regret = (top1_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
                selected_regret = (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0

                top1_by_graph[item["graph_id"]].append(top1_regret)
                selector_by_graph[item["graph_id"]].append(selected_regret)
                runtime_by_graph[item["graph_id"]].append(runtime)
                probes.append(int(probe))
                actions.append(action_count)

    top1 = _summary(top1_by_graph)
    selector = _summary(selector_by_graph)
    delta = [
        _mean(selector_by_graph[graph_id]) - _mean(top1_by_graph[graph_id])
        for graph_id in sorted(top1_by_graph)
    ]
    lower, upper = bootstrap_mean_ci(
        delta,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "threshold": threshold,
        "selector": selector,
        "delta_vs_top1": {
            "mean": _mean(delta),
            "bootstrap_95_ci": [lower, upper],
            "better_graphs": sum(value < 0 for value in delta),
            "worse_graphs": sum(value > 0 for value in delta),
            "ties": sum(value == 0 for value in delta),
        },
        "probe_rate": _mean(probes),
        "mean_actions": _mean(actions),
        "mean_runtime_seconds": _mean(
            [value for values in runtime_by_graph.values() for value in values]
        ),
    }


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    corpora = sorted({item["corpus"] for item in records})
    cells = [
        _evaluate_threshold(records, corpora, threshold)
        for threshold in THRESHOLDS
    ]
    return {
        "schema_version": "1.0",
        "protocol": "training-only trigger-threshold sensitivity for oracle-free online top-k selector",
        "benchmark_commit": payload.get("commit_sha"),
        "thresholds": list(THRESHOLDS),
        "selection_policy": (
            "Same frozen selector as PR #100; only the minimum predicted relative "
            "benefit required to trigger one alternate probe is varied. No cell is selected automatically."
        ),
        "cells": cells,
        "evidence_boundary": [
            "All predictions are fitted within each leave-one-corpus-out training fold.",
            "Held-out seed outcomes are used only for evaluation.",
            "The threshold grid is fixed before reading the held-out results.",
            "No production/default behavior changes.",
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
