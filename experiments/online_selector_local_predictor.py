from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import _distance, topology_vector
from atof.statistics import bootstrap_mean_ci
from experiments.online_topk_selector import (
    _build_records,
    _fit,
    _load,
    _mean,
    _predict_alternate,
)
from experiments.selector_threshold_sensitivity import _training_predictor

LOCAL_KS = (3, 5, 7)
THRESHOLDS = (0.0, 0.005, 0.008, 0.009)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _graph_pair_data(training: list[dict], router) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in training:
        ranking = router.rank(item["topology"])
        if len(ranking) < 3:
            continue
        top1 = ranking[0]
        top1_values = item["by_seed"]
        for rank in (1, 2):
            candidate = ranking[rank]
            deltas = []
            for candidates in top1_values.values():
                top1_cut = candidates[top1]["edge_cut"]
                candidate_cut = candidates[candidate]["edge_cut"]
                if top1_cut:
                    deltas.append((candidate_cut - top1_cut) / top1_cut)
            if not deltas:
                continue
            out[(top1, candidate)].append(
                {
                    "graph_id": item["graph_id"],
                    "topology": item["topology"],
                    "delta": _mean(deltas),
                }
            )
    return out


def _local_predict(
    item: dict,
    ranking: tuple[str, ...],
    pair_data: dict[tuple[str, str], list[dict]],
    router,
    k: int,
) -> tuple[str, float, dict]:
    predictions = []
    target_vector = topology_vector(item["topology"], router.features)
    for rank in (1, 2):
        candidate = ranking[rank]
        key = (ranking[0], candidate)
        samples = pair_data.get(key, [])
        scored = []
        for sample in samples:
            vector = topology_vector(sample["topology"], router.features)
            distance = _distance(
                target_vector,
                vector,
                router._scale,
                router.metric,
            )
            scored.append((distance, sample["delta"], sample["graph_id"]))
        scored.sort(key=lambda row: (row[0], row[2]))
        neighbors = scored[:k]
        if neighbors:
            prediction = _median([row[1] for row in neighbors])
            support = len(neighbors)
            max_distance = neighbors[-1][0]
        else:
            prediction = None
            support = 0
            max_distance = None
        predictions.append((prediction, rank, candidate, support, max_distance))

    usable = [row for row in predictions if row[0] is not None]
    if usable:
        chosen = min(
            usable,
            key=lambda row: (row[0], row[1], row[2]),
        )
        return chosen[2], float(chosen[0]), {
            "support": chosen[3],
            "neighbor_radius": chosen[4],
            "source": "local",
        }

    pair_median, candidate_median, rank_median = _training_predictor(
        [], router
    )
    # The fallback above is intentionally unreachable for a valid current
    # benchmark because the caller supplies an explicit global fallback.
    raise RuntimeError("local predictor has no usable pair and no fallback")


def _local_predict_with_fallback(
    item: dict,
    ranking: tuple[str, ...],
    pair_data: dict[tuple[str, str], list[dict]],
    router,
    k: int,
    global_pair: dict[tuple[str, str], float],
    global_candidate: dict[str, float],
    global_rank: dict[int, float],
) -> tuple[str, float, dict]:
    predictions = []
    target_vector = topology_vector(item["topology"], router.features)
    for rank in (1, 2):
        candidate = ranking[rank]
        key = (ranking[0], candidate)
        samples = pair_data.get(key, [])
        scored = []
        for sample in samples:
            vector = topology_vector(sample["topology"], router.features)
            distance = _distance(
                target_vector,
                vector,
                router._scale,
                router.metric,
            )
            scored.append((distance, sample["delta"], sample["graph_id"]))
        scored.sort(key=lambda row: (row[0], row[2]))
        neighbors = scored[:k]
        if neighbors:
            prediction = _median([row[1] for row in neighbors])
            metadata = {
                "source": "local",
                "support": len(neighbors),
                "neighbor_radius": neighbors[-1][0],
                "neighbor_ids": [row[2] for row in neighbors],
            }
        else:
            prediction = global_pair.get(
                key,
                global_candidate.get(candidate, global_rank.get(rank, 0.0)),
            )
            metadata = {
                "source": "global_fallback",
                "support": 0,
                "neighbor_radius": None,
                "neighbor_ids": [],
            }
        predictions.append((prediction, rank, candidate, metadata))

    prediction, _, candidate, metadata = min(
        predictions,
        key=lambda row: (row[0], row[1], row[2]),
    )
    return candidate, float(prediction), metadata


def _global_manifest(records: list[dict]) -> dict[tuple[str, str], list[dict]]:
    # Kept separate so diagnostics compare an identical training corpus under
    # the existing global predictor and the new local predictor.
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    return out


def _evaluate(records: list[dict], mode: str, local_k: int | None, threshold: float) -> dict:
    corpora = sorted({item["corpus"] for item in records})
    predicted_by_graph: dict[str, float] = {}
    realized_by_graph: dict[str, float] = {}
    selector_regret: dict[str, list[float]] = defaultdict(list)
    top1_regret: dict[str, list[float]] = defaultdict(list)
    probe_flags: list[int] = []
    actions: list[int] = []
    metadata: dict[str, dict] = {}

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)
        pair_median, candidate_median, rank_median = _training_predictor(
            training, router
        )
        pair_data = _graph_pair_data(training, router) if mode == "local" else {}

        for item in test:
            ranking = router.rank(item["topology"])
            if mode == "global":
                alternate, predicted_delta = _predict_alternate(
                    ranking,
                    pair_median=pair_median,
                    candidate_median=candidate_median,
                    rank_median=rank_median,
                )
                prediction_meta = {
                    "source": "global",
                    "support": None,
                    "neighbor_radius": None,
                    "neighbor_ids": [],
                }
            else:
                alternate, predicted_delta, prediction_meta = _local_predict_with_fallback(
                    item,
                    ranking,
                    pair_data,
                    router,
                    int(local_k),
                    pair_median,
                    candidate_median,
                    rank_median,
                )

            top1 = ranking[0]
            probe = predicted_delta < -threshold
            realized_values = []
            for candidates in item["by_seed"].values():
                oracle = min(
                    candidates,
                    key=lambda name: (candidates[name]["edge_cut"], name),
                )
                oracle_cut = candidates[oracle]["edge_cut"]
                top1_cut = candidates[top1]["edge_cut"]
                alternate_cut = candidates[alternate]["edge_cut"]
                realized_delta = (
                    (alternate_cut - top1_cut) / top1_cut
                    if top1_cut
                    else 0.0
                )
                realized_values.append(realized_delta)

                if probe:
                    selected_cut = min(top1_cut, alternate_cut)
                    action_count = 2
                else:
                    selected_cut = top1_cut
                    action_count = 1

                top1_value = (top1_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
                selected_value = (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
                top1_regret[item["graph_id"]].append(top1_value)
                selector_regret[item["graph_id"]].append(selected_value)
                probe_flags.append(int(probe))
                actions.append(action_count)

            predicted_by_graph[item["graph_id"]] = predicted_delta
            realized_by_graph[item["graph_id"]] = _mean(realized_values)
            metadata[item["graph_id"]] = prediction_meta

    graph_ids = sorted(predicted_by_graph)
    predicted = [predicted_by_graph[g] for g in graph_ids]
    realized = [realized_by_graph[g] for g in graph_ids]
    errors = [r - p for r, p in zip(realized, predicted)]
    error_low, error_high = bootstrap_mean_ci(errors, resamples=5000, seed=2024)

    paired_delta = [
        _mean(selector_regret[g]) - _mean(top1_regret[g])
        for g in graph_ids
    ]
    delta_low, delta_high = bootstrap_mean_ci(
        paired_delta,
        resamples=5000,
        seed=2024,
    )

    return {
        "mode": mode,
        "local_k": local_k,
        "threshold": threshold,
        "graphs": len(graph_ids),
        "prediction": {
            "mean_prediction_error": _mean(errors),
            "mae_prediction_error": _mean([abs(value) for value in errors]),
            "bootstrap_95_ci_mean_error": [error_low, error_high],
            "negative_predictions": sum(value < 0 for value in predicted),
            "negative_realized": sum(value < 0 for value in realized),
        },
        "selector": {
            "mean_graph_regret": _mean([_mean(selector_regret[g]) for g in graph_ids]),
            "paired_delta_vs_top1": _mean(paired_delta),
            "bootstrap_95_ci_delta_vs_top1": [delta_low, delta_high],
            "better_graphs": sum(value < 0 for value in paired_delta),
            "worse_graphs": sum(value > 0 for value in paired_delta),
            "ties": sum(value == 0 for value in paired_delta),
            "probe_rate": _mean(probe_flags),
            "mean_actions": _mean(actions),
        },
        "graph_manifest": [
            {
                "graph_id": g,
                "predicted_relative_delta": predicted_by_graph[g],
                "realized_mean_relative_delta": realized_by_graph[g],
                "prediction_metadata": metadata[g],
            }
            for g in graph_ids
        ],
    }


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)

    cells = []
    cells.append(_evaluate(records, "global", None, 0.0))
    cells.extend(
        _evaluate(records, "local", k, threshold)
        for k in LOCAL_KS
        for threshold in THRESHOLDS
    )
    return {
        "schema_version": "1.0",
        "protocol": (
            "diagnostic comparison of frozen global-pair predictor versus "
            "topology-local training-only pair predictor"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "local_k_values": list(LOCAL_KS),
        "thresholds": list(THRESHOLDS),
        "cells": cells,
        "evidence_boundary": [
            "Each prediction is fitted only within its leave-one-corpus-out training fold.",
            "Local neighbors are training graphs only and use topology distance under the frozen router scaling.",
            "Held-out outcomes are evaluation only.",
            "The local-k and threshold grids are fixed in advance and no cell is selected automatically.",
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
