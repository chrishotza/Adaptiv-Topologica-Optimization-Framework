from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.statistics import bootstrap_mean_ci
from experiments.selector_threshold_sensitivity import (
    RESAMPLES,
    BOOTSTRAP_SEED,
    _evaluate_threshold,
)
from experiments.online_topk_selector import (
    _build_records,
    _fit,
    _load,
    _predict_alternate,
)

# Follow-up localization grid chosen after PR #101. This is diagnostic, not
# a production/default parameter search.
THRESHOLDS = (
    0.0050,
    0.0060,
    0.0070,
    0.0080,
    0.0090,
    0.0100,
    0.0110,
    0.0125,
    0.0150,
    0.0200,
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _predictor_manifest(records: list[dict]) -> list[dict]:
    corpora = sorted({item["corpus"] for item in records})
    outputs: list[dict] = []

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)

        # Rebuild the same training-only predictor used by PR #100/#101.
        from experiments.selector_threshold_sensitivity import _training_predictor

        pair_median, candidate_median, rank_median = _training_predictor(
            training, router
        )

        for item in test:
            ranking = router.rank(item["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            outputs.append(
                {
                    "heldout_corpus": heldout,
                    "graph_id": item["graph_id"],
                    "alternate": alternate,
                    "alternate_rank": list(ranking).index(alternate) + 1,
                    "predicted_relative_delta": predicted_delta,
                }
            )

    return sorted(outputs, key=lambda row: row["graph_id"])


def _threshold_activation_summary(
    predictions: list[dict],
    threshold: float,
) -> dict:
    active = [
        row
        for row in predictions
        if row["predicted_relative_delta"] < -threshold
    ]
    inactive = [
        row
        for row in predictions
        if row["predicted_relative_delta"] >= -threshold
    ]
    return {
        "threshold": threshold,
        "graph_count": len(predictions),
        "active_graphs": len(active),
        "inactive_graphs": len(inactive),
        "graph_probe_rate": (
            len(active) / len(predictions) if predictions else 0.0
        ),
        "active_graph_ids": [row["graph_id"] for row in active],
        "active_predicted_relative_deltas": [
            row["predicted_relative_delta"] for row in active
        ],
    }


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    predictions = _predictor_manifest(records)
    cells = [
        _evaluate_threshold(
            records,
            sorted({item["corpus"] for item in records}),
            threshold,
        )
        for threshold in THRESHOLDS
    ]

    activation = [
        _threshold_activation_summary(predictions, threshold)
        for threshold in THRESHOLDS
    ]

    predicted_values = [row["predicted_relative_delta"] for row in predictions]
    lower, upper = bootstrap_mean_ci(
        predicted_values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    return {
        "schema_version": "1.0",
        "protocol": (
            "post-PR-101 diagnostic localization of the online-selector "
            "trigger transition; thresholds are fixed before held-out "
            "evaluation within this experiment and are not auto-selected"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "thresholds": list(THRESHOLDS),
        "prediction_distribution": {
            "graphs": len(predictions),
            "mean_predicted_relative_delta": _mean(predicted_values),
            "bootstrap_95_ci": [lower, upper],
            "min": min(predicted_values),
            "max": max(predicted_values),
        },
        "activation": activation,
        "performance_cells": cells,
        "predictor_manifest": predictions,
        "evidence_boundary": [
            "The transition grid was fixed in this research branch before the held-out benchmark was evaluated.",
            "All trigger predictions are fitted within each leave-one-corpus-out training fold.",
            "Held-out outcomes are used only to evaluate each threshold cell.",
            "No threshold is selected automatically.",
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
    print(json.dumps({
        "activation": result["activation"],
        "performance_cells": result["performance_cells"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
