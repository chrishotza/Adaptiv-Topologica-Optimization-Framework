from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from atof.routing import FEATURE_GROUPS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from experiments.k8_degree_hub_replication import _graph_record
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora

K = 8
SEEDS = (7001, 8192, 104729, 131071, 262144)
BOOTSTRAP_SEED = 2024
RESAMPLES = 5000

HYBRID_FEATURES = (
    *FEATURE_GROUPS["degree_hub"],
    *FEATURE_GROUPS["global_paths"],
)

ROUTER_CONFIGS = {
    "all_iqr_l2": tuple(FEATURE_GROUPS["all"]),
    "degree_hub_iqr_l2": tuple(FEATURE_GROUPS["degree_hub"]),
    "global_paths_iqr_l2": tuple(FEATURE_GROUPS["global_paths"]),
    "degree_hub_global_paths_iqr_l2": HYBRID_FEATURES,
}


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _regret(record: dict, strategy: str) -> float:
    oracle_cut = float(record["strategy_means"][record["oracle_strategy"]])
    selected_cut = float(record["strategy_means"][strategy])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def _fit(training: list[dict], features: tuple[str, ...]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in training
    ]
    return LearnedTopologyRouter(
        features=features,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)


def _evaluate(
    records_by_corpus: dict[str, list[dict]],
    features: tuple[str, ...],
) -> dict:
    values_by_graph: dict[str, list[float]] = defaultdict(list)
    decisions: dict[str, str] = {}
    folds = []

    for heldout, test_records in sorted(records_by_corpus.items()):
        training = [
            record
            for corpus, corpus_records in records_by_corpus.items()
            if corpus != heldout
            for record in corpus_records
        ]
        router = _fit(training, features)

        fold_values = []
        for record in sorted(test_records, key=lambda item: item["graph_id"]):
            selected = router.predict(record["topology"])
            value = _regret(record, selected)
            values_by_graph[record["graph_id"]].append(value)
            decisions[record["graph_id"]] = selected
            fold_values.append(value)

        folds.append(
            {
                "test_corpus": heldout,
                "graphs": len(fold_values),
                "mean_relative_regret": _mean(fold_values),
            }
        )

    graph_values = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_values.values())
    low, high = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "features": list(features),
        "graphs": len(values),
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": [low, high],
        "graph_values": graph_values,
        "decisions": decisions,
        "folds": folds,
    }


def _majority_evaluate(records_by_corpus: dict[str, list[dict]]) -> dict:
    values_by_graph: dict[str, list[float]] = defaultdict(list)
    decisions: dict[str, str] = {}

    for heldout, test_records in sorted(records_by_corpus.items()):
        training = [
            record
            for corpus, corpus_records in records_by_corpus.items()
            if corpus != heldout
            for record in corpus_records
        ]
        counts = Counter(record["oracle_strategy"] for record in training)
        majority = min(
            counts,
            key=lambda strategy: (-counts[strategy], strategy),
        )
        for record in sorted(test_records, key=lambda item: item["graph_id"]):
            values_by_graph[record["graph_id"]].append(_regret(record, majority))
            decisions[record["graph_id"]] = majority

    graph_values = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_values.values())
    low, high = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": [low, high],
        "graph_values": graph_values,
        "decisions": decisions,
    }


def run(output_path: str | Path, cache_dir: str | Path | None = None) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    records_by_corpus = {
        corpus: [
            _graph_record(graph, corpus, name, seeds=SEEDS)
            for name, graph in sorted(graphs.items())
        ]
        for corpus, graphs in sorted(corpora.items())
    }

    if sum(len(records) for records in records_by_corpus.values()) != 20:
        raise AssertionError("expected 20 graphs")

    if any(
        seed in {7, 42, 101, 1337, 1618, 2024, 2718, 3141, 8191, 65537}
        for seed in SEEDS
    ):
        raise AssertionError("seed grid overlaps prior k=8 routing seeds")

    seed_counts = {
        len(record["seed_oracles"])
        for records in records_by_corpus.values()
        for record in records
    }
    if seed_counts != {len(SEEDS)}:
        raise AssertionError("fresh seed grid incomplete")

    evaluations = {
        name: _evaluate(records_by_corpus, features)
        for name, features in ROUTER_CONFIGS.items()
    }
    majority = _majority_evaluate(records_by_corpus)

    result = {
        "schema_version": "1.0",
        "protocol": (
            "frozen k=8 hybrid representation confirmatory gate; "
            "candidate frozen before generating new solver outcomes"
        ),
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": K,
        "seeds": list(SEEDS),
        "seed_grid_status": "unused by prior k=8 routing experiments",
        "candidate_status": (
            "degree_hub_global_paths was chosen from a prior post-hoc diagnostic; "
            "this run is the confirmatory test on a fresh solver seed grid"
        ),
        "candidate_features": list(HYBRID_FEATURES),
        "candidate_strategies": list(
            next(
                record["strategy_means"].keys()
                for records in records_by_corpus.values()
                for record in records
            )
        ),
        "graphs": 20,
        "corpora": {
            corpus: {
                "graphs": len(records),
                "provenance": provenance[corpus],
            }
            for corpus, records in records_by_corpus.items()
        },
        "routers": evaluations,
        "majority_control": majority,
        "paired_hybrid_minus_all": {
            "graph_values": {
                graph_id: evaluations["degree_hub_global_paths_iqr_l2"]["graph_values"][graph_id]
                - evaluations["all_iqr_l2"]["graph_values"][graph_id]
                for graph_id in sorted(evaluations["all_iqr_l2"]["graph_values"])
            }
        },
        "graph_manifest": [
            record
            for records in records_by_corpus.values()
            for record in records
        ],
        "evidence_boundary": [
            "The hybrid feature set was frozen before these new solver outcomes were generated.",
            "The hybrid candidate was selected only from a prior post-hoc diagnostic and is not itself confirmatory evidence.",
            "These solver outcomes use five seeds not used in prior k=8 routing experiments.",
            "The graph corpus is intentionally unchanged; this gate is fresh-outcome confirmation, not external graph-domain validation.",
            "All routers use leave-one-corpus-out training, IQR scaling, and L2 distance.",
            "The held-out oracle is used only for evaluation.",
            "No production/default routing behavior changes.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                name: value["mean_relative_regret"]
                for name, value in evaluations.items()
            }
            | {"majority": majority["mean_relative_regret"]},
            indent=2,
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    run(args.output, args.cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
