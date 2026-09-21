from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from atof.generalization import summarize_transfer_folds
from atof.routing import (
    FEATURE_ABLATIONS,
    LearnedTopologyRouter,
    NearestTopologyRouter,
)
from experiments.run_cross_corpus_transfer import (
    _benchmark_graph,
    _choose_majority_strategy,
    _load_corpora,
    _relative_metrics,
)


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _run_feature_set(
    records: dict[str, dict[str, dict]],
    features: tuple[str, ...],
) -> dict:
    selector_map = {
        "hub_dominated": "bloc_reloc_affinity",
        "modular": "bloc_reloc_baseline",
        "regular_like": "bloc_reloc_baseline",
        "mixed": "bloc_reloc_baseline",
    }
    summaries: dict[str, dict] = {}
    folds_by_corpus: dict[str, list[dict]] = {}

    for test_corpus, test_graphs in records.items():
        training_graphs = [
            record
            for corpus, graphs in records.items()
            if corpus != test_corpus
            for record in graphs.values()
        ]

        centroid = LearnedTopologyRouter(features=features).fit(training_graphs)
        nearest = NearestTopologyRouter(features=features).fit(training_graphs)
        majority = _choose_majority_strategy(training_graphs)

        folds: list[dict] = []
        for record in test_graphs.values():
            oracle = record["oracle_strategy"]
            centroid_strategy = centroid.predict(record["topology"])
            nearest_strategy = nearest.predict(record["topology"])
            heuristic_strategy = selector_map[record["regime"]]

            centroid_abs, centroid_rel = _relative_metrics(
                centroid_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle,
            )
            nearest_abs, nearest_rel = _relative_metrics(
                nearest_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle,
            )
            majority_abs, majority_rel = _relative_metrics(
                majority,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle,
            )
            heuristic_abs, heuristic_rel = _relative_metrics(
                heuristic_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle,
            )

            folds.append({
                "test_corpus": test_corpus,
                "held_out_graph": record["graph"],
                "oracle_strategy": oracle,
                "learned_strategy": centroid_strategy,
                "nearest_strategy": nearest_strategy,
                "majority_strategy": majority,
                "heuristic_strategy": heuristic_strategy,
                "learned_absolute_regret": centroid_abs,
                "nearest_absolute_regret": nearest_abs,
                "majority_absolute_regret": majority_abs,
                "heuristic_absolute_regret": heuristic_abs,
                "learned_relative_regret": centroid_rel,
                "nearest_relative_regret": nearest_rel,
                "majority_relative_regret": majority_rel,
                "heuristic_relative_regret": heuristic_rel,
            })

        folds_by_corpus[test_corpus] = folds
        summaries[test_corpus] = summarize_transfer_folds(
            folds,
            test_corpus=test_corpus,
        )

    nonempty = [value for value in summaries.values() if value["graphs"]]
    macro = {
        "learned_mean_relative_regret": _mean(
            value["learned_mean_relative_regret"] for value in nonempty
        ),
        "nearest_mean_relative_regret": _mean(
            value["nearest_mean_relative_regret"] for value in nonempty
        ),
        "majority_mean_relative_regret": _mean(
            value["majority_mean_relative_regret"] for value in nonempty
        ),
        "heuristic_mean_relative_regret": _mean(
            value["heuristic_mean_relative_regret"] for value in nonempty
        ),
        "learned_oracle_agreement": _mean(
            value["learned_oracle_agreement"] for value in nonempty
        ),
        "nearest_oracle_agreement": _mean(
            value["nearest_oracle_agreement"] for value in nonempty
        ),
        "majority_oracle_agreement": _mean(
            value["majority_oracle_agreement"] for value in nonempty
        ),
        "heuristic_oracle_agreement": _mean(
            value["heuristic_oracle_agreement"] for value in nonempty
        ),
    }
    return {
        "features": list(features),
        "corpora": summaries,
        "folds": folds_by_corpus,
        "macro": macro,
    }


def run_feature_ablation(
    output_path: str | Path = "results/generalization/feature_ablation.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    """Evaluate router feature-set transfer with the same corpus LOO protocol."""
    if k != 2:
        raise ValueError("The feature ablation protocol currently requires k=2.")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)

    records = {
        corpus: {
            name: _benchmark_graph(
                graph,
                corpus=corpus,
                name=name,
                k=k,
                seeds=seeds,
                iterations=iterations,
            )
            for name, graph in graphs.items()
        }
        for corpus, graphs in corpora.items()
    }

    studies = {
        name: _run_feature_set(
            records,
            tuple(features),
        )
        for name, features in FEATURE_ABLATIONS.items()
    }

    payload = {
        "schema_version": "0.1",
        "protocol": "leave-one-corpus-out topology-feature ablation",
        "unit_of_analysis": "held-out graph",
        "created_at": time.time(),
        "python": sys.version,
        "platform": platform.platform(),
        "commit_sha": _commit_sha(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "feature_sets": studies,
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "interpretation": [
            "Feature subsets are tested without changing the candidate strategy set or partition objective.",
            "The complete test corpus is excluded from router training.",
            "Majority and heuristic controls are retained for every feature set.",
            "This is an ablation study, not a claim that a feature group is universally causal for routing success.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_feature_ablation()
    print(
        json.dumps(
            {
                name: value["macro"]
                for name, value in result["feature_sets"].items()
            },
            indent=2,
        )
    )
