from __future__ import annotations

import argparse
import json
import random
from math import comb
from pathlib import Path
from statistics import mean


BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 2024


def exact_two_sided_sign_test(deltas: list[float]) -> float:
    non_ties = [value for value in deltas if value != 0]
    n = len(non_ties)
    if n == 0:
        return 1.0
    negatives = sum(value < 0 for value in non_ties)
    tail = sum(comb(n, i) for i in range(min(negatives, n - negatives) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def bootstrap_mean_ci(
    deltas: list[float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> list[float]:
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(resamples):
        means.append(mean(deltas[rng.randrange(n)] for _ in range(n)))
    means.sort()
    low = means[int(0.025 * resamples)]
    high = means[int(0.975 * resamples) - 1]
    return [low, high]


def run_robustness(payload: dict) -> dict:
    results = {}
    for config_name, config in payload["configs"].items():
        rows = [
            row
            for fold in config["folds"].values()
            for row in fold
        ]
        config_result = {}
        for router_name, metric_key in (
            ("nearest", "nearest_relative_regret"),
            ("centroid", "learned_relative_regret"),
        ):
            deltas = [
                row[metric_key] - row["majority_relative_regret"]
                for row in rows
            ]
            corpus_mean_delta = {
                corpus: mean(
                    row[metric_key] - row["majority_relative_regret"]
                    for row in fold_rows
                )
                for corpus, fold_rows in config["folds"].items()
            }
            config_result[router_name] = {
                "mean_delta": mean(deltas),
                "bootstrap_95_ci": bootstrap_mean_ci(deltas),
                "better": sum(value < 0 for value in deltas),
                "worse": sum(value > 0 for value in deltas),
                "ties": sum(value == 0 for value in deltas),
                "sign_test_p": exact_two_sided_sign_test(deltas),
                "corpus_mean_delta": corpus_mean_delta,
            }
        results[config_name] = results.get(config_name, {})
        results[config_name].update(config_result)

    return {
        "schema_version": "1.0",
        "source_total_graphs": payload["total_graphs"],
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "comparison": "router relative regret minus majority relative regret",
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run_robustness(payload)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
