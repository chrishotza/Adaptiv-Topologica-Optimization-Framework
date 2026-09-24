from __future__ import annotations

import argparse
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path

from atof.statistics import bootstrap_mean_ci
from experiments.online_topk_selector import (
    _build_records,
    _fit,
    _load,
    _predict_alternate,
)
from experiments.selector_threshold_sensitivity import _training_predictor

# Fixed diagnostic bins chosen before running the fresh held-out benchmark.
PREDICTION_BINS = (
    ("<=-1%", float("-inf"), -0.01),
    ("(-1%,-0.5%]", -0.01, -0.005),
    ("(-0.5%,0%)", -0.005, 0.0),
    ("[0%,0.5%)", 0.0, 0.005),
    ("[0.5%,1%)", 0.005, 0.01),
    (">=1%", 0.01, float("inf")),
)
THRESHOLDS = (0.005, 0.008, 0.009, 0.01)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ma, mb = _mean(a), _mean(b)
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    denom = sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    return sum(x * y for x, y in zip(da, db)) / denom if denom else 0.0


def _rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: (pair[1], pair[0]))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = rank
        i = j + 1
    return ranks


def _spearman(a: list[float], b: list[float]) -> float:
    return _pearson(_rank(a), _rank(b))


def _build_manifest(records: list[dict]) -> list[dict]:
    corpora = sorted({item["corpus"] for item in records})
    outputs: list[dict] = []

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)
        pair_median, candidate_median, rank_median = _training_predictor(
            training, router
        )

        for item in test:
            ranking = router.rank(item["topology"])
            top1 = ranking[0]
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )

            per_seed = []
            for seed, candidates in sorted(item["by_seed"].items()):
                top1_cut = candidates[top1]["edge_cut"]
                alternate_cut = candidates[alternate]["edge_cut"]
                realized_delta = (
                    (alternate_cut - top1_cut) / top1_cut
                    if top1_cut
                    else 0.0
                )
                per_seed.append(
                    {
                        "seed": seed,
                        "top1_cut": top1_cut,
                        "alternate_cut": alternate_cut,
                        "realized_relative_delta": realized_delta,
                        "alternate_better": alternate_cut < top1_cut,
                    }
                )

            realized_values = [
                row["realized_relative_delta"] for row in per_seed
            ]
            outputs.append(
                {
                    "heldout_corpus": heldout,
                    "graph_id": item["graph_id"],
                    "top1": top1,
                    "alternate": alternate,
                    "alternate_rank": list(ranking).index(alternate) + 1,
                    "predicted_relative_delta": predicted_delta,
                    "realized_mean_relative_delta": _mean(realized_values),
                    "realized_seed_std": _std(realized_values),
                    "alternate_better_seed_rate": _mean(
                        [float(row["alternate_better"]) for row in per_seed]
                    ),
                    "per_seed": per_seed,
                }
            )

    return sorted(outputs, key=lambda row: row["graph_id"])


def _bin_name(value: float) -> str:
    for name, low, high in PREDICTION_BINS:
        if low <= value < high:
            return name
    return PREDICTION_BINS[-1][0]


def _bin_summary(manifest: list[dict]) -> list[dict]:
    out = []
    for name, low, high in PREDICTION_BINS:
        rows = [
            row
            for row in manifest
            if low <= row["predicted_relative_delta"] < high
        ]
        realized = [row["realized_mean_relative_delta"] for row in rows]
        predicted = [row["predicted_relative_delta"] for row in rows]
        out.append(
            {
                "bin": name,
                "graphs": len(rows),
                "mean_predicted_relative_delta": _mean(predicted),
                "mean_realized_relative_delta": _mean(realized),
                "mean_prediction_error": _mean(
                    [r - p for r, p in zip(realized, predicted)]
                ),
                "alternate_better_seed_rate": _mean(
                    [row["alternate_better_seed_rate"] for row in rows]
                ),
            }
        )
    return out


def _threshold_summary(manifest: list[dict], threshold: float) -> dict:
    active = [
        row
        for row in manifest
        if row["predicted_relative_delta"] < -threshold
    ]
    realized = [row["realized_mean_relative_delta"] for row in active]
    sign_hits = sum(value < 0 for value in realized)
    seed_rates = [row["alternate_better_seed_rate"] for row in active]
    return {
        "threshold": threshold,
        "active_graphs": len(active),
        "graph_activation_rate": len(active) / len(manifest) if manifest else 0.0,
        "mean_predicted_relative_delta": _mean(
            [row["predicted_relative_delta"] for row in active]
        ),
        "mean_realized_relative_delta": _mean(realized),
        "realized_negative_graphs": sign_hits,
        "realized_negative_graph_rate": (
            sign_hits / len(active) if active else 0.0
        ),
        "alternate_better_seed_rate": _mean(seed_rates),
        "active_graphs_detail": [
            {
                "graph_id": row["graph_id"],
                "predicted_relative_delta": row["predicted_relative_delta"],
                "realized_mean_relative_delta": row["realized_mean_relative_delta"],
                "alternate_better_seed_rate": row["alternate_better_seed_rate"],
            }
            for row in active
        ],
    }


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    manifest = _build_manifest(records)

    predicted = [row["predicted_relative_delta"] for row in manifest]
    realized = [row["realized_mean_relative_delta"] for row in manifest]
    errors = [r - p for r, p in zip(realized, predicted)]
    lower, upper = bootstrap_mean_ci(
        errors,
        resamples=5000,
        seed=2024,
    )

    return {
        "schema_version": "1.0",
        "protocol": (
            "training-only predictor calibration against held-out realized "
            "alternate-vs-top1 deltas; diagnostic only"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "prediction_bins": [
            {"name": name, "low": low, "high": high}
            for name, low, high in PREDICTION_BINS
        ],
        "thresholds": list(THRESHOLDS),
        "aggregate": {
            "graphs": len(manifest),
            "mean_prediction_error": _mean(errors),
            "mae_prediction_error": _mean([abs(value) for value in errors]),
            "bootstrap_95_ci_mean_prediction_error": [lower, upper],
            "pearson_prediction_vs_realized": _pearson(predicted, realized),
            "spearman_prediction_vs_realized": _spearman(predicted, realized),
            "negative_prediction_graphs": sum(value < 0 for value in predicted),
            "negative_realized_graphs": sum(value < 0 for value in realized),
            "sign_agreement_rate": _mean(
                [
                    float((p < 0) == (r < 0))
                    for p, r in zip(predicted, realized)
                ]
            ),
        },
        "bins": _bin_summary(manifest),
        "thresholds": [
            _threshold_summary(manifest, threshold)
            for threshold in THRESHOLDS
        ],
        "graph_manifest": manifest,
        "evidence_boundary": [
            "Predictions are fitted within leave-one-corpus-out training folds.",
            "Realized alternate-vs-top1 outcomes come only from held-out seeds.",
            "Prediction bins and diagnostic thresholds are fixed before benchmark execution.",
            "No production/default behavior changes.",
            "Calibration does not select or promote a threshold automatically.",
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
    print(json.dumps({
        "aggregate": result["aggregate"],
        "bins": result["bins"],
        "thresholds": result["thresholds"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
