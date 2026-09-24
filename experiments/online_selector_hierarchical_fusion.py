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
RADIUS_THRESHOLDS = (5.0, 7.5, 10.0, 12.5, 15.0, 20.0)


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
        for rank in (1, 2):
            candidate = ranking[rank]
            deltas = []
            for candidates in item["by_seed"].values():
                top1_cut = candidates[top1]["edge_cut"]
                candidate_cut = candidates[candidate]["edge_cut"]
                if top1_cut:
                    deltas.append((candidate_cut - top1_cut) / top1_cut)
            if deltas:
                out[(top1, candidate)].append(
                    {
                        "graph_id": item["graph_id"],
                        "topology": item["topology"],
                        "delta": _mean(deltas),
                    }
                )
    return out


def _local_candidates(
    item: dict,
    ranking: tuple[str, ...],
    pair_data: dict[tuple[str, str], list[dict]],
    router,
    k: int,
) -> list[dict]:
    target = topology_vector(item["topology"], router.features)
    out = []
    for rank in (1, 2):
        candidate = ranking[rank]
        samples = pair_data.get((ranking[0], candidate), [])
        scored = []
        for sample in samples:
            vector = topology_vector(sample["topology"], router.features)
            distance = _distance(target, vector, router._scale, router.metric)
            scored.append((distance, sample["delta"], sample["graph_id"]))
        scored.sort(key=lambda row: (row[0], row[2]))
        neighbors = scored[:k]
        if neighbors:
            out.append(
                {
                    "rank": rank,
                    "candidate": candidate,
                    "prediction": _median([row[1] for row in neighbors]),
                    "radius": neighbors[-1][0],
                    "support": len(neighbors),
                    "neighbor_ids": [row[2] for row in neighbors],
                }
            )
    return out


def _fused_prediction(
    global_prediction: float,
    local: list[dict],
    radius_threshold: float,
    orientation: str,
) -> tuple[str, float, dict]:
    candidates = []
    for row in local:
        use_global = (
            row["radius"] <= radius_threshold
            if orientation == "global_near"
            else row["radius"] > radius_threshold
        )
        prediction = global_prediction if use_global else row["prediction"]
        source = "global" if use_global else "local"
        candidates.append((prediction, row["rank"], row["candidate"], source, row))

    if not candidates:
        raise RuntimeError("no local candidate support")
    prediction, rank, candidate, source, row = min(
        candidates,
        key=lambda item: (item[0], item[1], item[2]),
    )
    return candidate, float(prediction), {
        "source": source,
        "radius": row["radius"],
        "support": row["support"],
        "neighbor_ids": row["neighbor_ids"],
        "orientation": orientation,
        "global_prediction": global_prediction,
        "local_prediction": row["prediction"],
    }


def _evaluate(
    records: list[dict],
    k: int,
    radius_threshold: float,
    orientation: str,
) -> dict:
    corpora = sorted({item["corpus"] for item in records})
    selector_regret: dict[str, list[float]] = defaultdict(list)
    top1_regret: dict[str, list[float]] = defaultdict(list)
    predicted_by_graph = {}
    realized_by_graph = {}
    metadata = {}
    probes = []
    actions = []

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)
        pair_median, candidate_median, rank_median = _training_predictor(
            training, router
        )
        pair_data = _graph_pair_data(training, router)

        for item in test:
            ranking = router.rank(item["topology"])
            _, global_pred = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            top1 = ranking[0]
            local = _local_candidates(item, ranking, pair_data, router, k)

            if local:
                alternate, predicted, meta = _fused_prediction(
                    global_pred,
                    local,
                    radius_threshold,
                    orientation,
                )
            else:
                alternate, predicted = _predict_alternate(
                    ranking,
                    pair_median=pair_median,
                    candidate_median=candidate_median,
                    rank_median=rank_median,
                )
                meta = {
                    "source": "global_fallback",
                    "radius": None,
                    "support": 0,
                    "neighbor_ids": [],
                    "orientation": orientation,
                    "global_prediction": global_pred,
                    "local_prediction": None,
                }

            probe = predicted < 0.0
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

                selected_cut = min(top1_cut, alternate_cut) if probe else top1_cut
                selector_value = (
                    (selected_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                top1_value = (
                    (top1_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                selector_regret[item["graph_id"]].append(selector_value)
                top1_regret[item["graph_id"]].append(top1_value)
                probes.append(int(probe))
                actions.append(2 if probe else 1)

            predicted_by_graph[item["graph_id"]] = predicted
            realized_by_graph[item["graph_id"]] = _mean(realized_values)
            metadata[item["graph_id"]] = meta

    graph_ids = sorted(predicted_by_graph)
    paired_delta = [
        _mean(selector_regret[g]) - _mean(top1_regret[g])
        for g in graph_ids
    ]
    low, high = bootstrap_mean_ci(paired_delta, resamples=5000, seed=2024)

    return {
        "k": k,
        "radius_threshold": radius_threshold,
        "orientation": orientation,
        "graphs": len(graph_ids),
        "selector": {
            "mean_graph_regret": _mean([_mean(selector_regret[g]) for g in graph_ids]),
            "paired_delta_vs_top1": _mean(paired_delta),
            "bootstrap_95_ci_delta_vs_top1": [low, high],
            "better_graphs": sum(v < 0 for v in paired_delta),
            "worse_graphs": sum(v > 0 for v in paired_delta),
            "ties": sum(v == 0 for v in paired_delta),
            "probe_rate": _mean(probes),
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
    for orientation in ("global_near", "local_near"):
        for k in LOCAL_KS:
            for radius in RADIUS_THRESHOLDS:
                cells.append(_evaluate(records, k, radius, orientation))
    return {
        "schema_version": "1.0",
        "protocol": (
            "diagnostic hierarchical fusion of global pair predictor and "
            "topology-local pair predictor using fixed neighbor-radius gates"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "local_k_values": list(LOCAL_KS),
        "radius_thresholds": list(RADIUS_THRESHOLDS),
        "orientations": ["global_near", "local_near"],
        "cells": cells,
        "evidence_boundary": [
            "Each predictor is fitted only within its leave-one-corpus-out training fold.",
            "Held-out outcomes are evaluation only.",
            "The k and radius grids are fixed before the fresh benchmark and no cell is selected automatically.",
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
    print(json.dumps([
        {
            "k": c["k"],
            "radius_threshold": c["radius_threshold"],
            "orientation": c["orientation"],
            **c["selector"],
        }
        for c in result["cells"]
    ], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
