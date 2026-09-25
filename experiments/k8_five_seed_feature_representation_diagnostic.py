from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import FEATURE_GROUPS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

RESAMPLES = 5000
BOOTSTRAP_SEED = 2024
EXPECTED_GROUPS = ("all", "degree_hub", "mesoscopic", "global_paths")


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _summary(values: list[float]) -> dict:
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": [lower, upper],
    }


def _load(path: Path) -> tuple[dict, dict[str, list[dict]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise AssertionError("unexpected benchmark schema")
    if payload.get("k") != 8:
        raise AssertionError(f"expected k=8, got {payload.get('k')}")
    if payload.get("seeds") != [7, 42, 101, 2024, 8191]:
        raise AssertionError("expected the frozen five-seed grid")
    records = payload.get("graph_manifest")
    if not isinstance(records, list) or len(records) != 20:
        raise AssertionError("expected 20 graph records")
    if payload.get("candidate_strategies") is None or len(payload["candidate_strategies"]) != 8:
        raise AssertionError("expected eight strategies")

    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if "topology" not in record or "strategy_means" not in record or "oracle_strategy" not in record:
            raise AssertionError(f"incomplete record {record.get('graph_id')}")
        if set(record["strategy_means"]) != set(payload["candidate_strategies"]):
            raise AssertionError(f"strategy set mismatch in {record.get('graph_id')}")
        by_corpus[str(record["corpus"])].append(record)
    if len(by_corpus) != 4:
        raise AssertionError(f"expected four corpora, got {sorted(by_corpus)}")
    return payload, dict(by_corpus)


def _fit(records: list[dict], features: tuple[str, ...]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in records
    ]
    return LearnedTopologyRouter(
        features=features,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)


def _regret(record: dict, selected: str) -> float:
    oracle_cut = float(record["strategy_means"][record["oracle_strategy"]])
    selected_cut = float(record["strategy_means"][selected])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def _evaluate(by_corpus: dict[str, list[dict]], features: tuple[str, ...]) -> dict:
    values_by_graph: dict[str, list[float]] = defaultdict(list)
    folds = []

    for heldout in sorted(by_corpus):
        training = [
            record
            for corpus, corpus_records in by_corpus.items()
            if corpus != heldout
            for record in corpus_records
        ]
        router = _fit(training, features)
        fold_values = []
        for record in sorted(by_corpus[heldout], key=lambda item: item["graph_id"]):
            selected = router.predict(record["topology"])
            value = _regret(record, selected)
            values_by_graph[record["graph_id"]].append(value)
            fold_values.append(value)
        folds.append(
            {
                "test_corpus": heldout,
                "graphs": len(fold_values),
                "mean_relative_regret": _mean(fold_values),
            }
        )

    graph_ids = sorted(values_by_graph)
    graph_values = {
        graph_id: _mean(values_by_graph[graph_id])
        for graph_id in graph_ids
    }
    values = [graph_values[graph_id] for graph_id in graph_ids]
    return {
        "features": list(features),
        "graphs": len(graph_ids),
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": list(
            bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
        ),
        "graph_values": graph_values,
        "folds": folds,
    }


def run(path: Path) -> dict:
    payload, by_corpus = _load(path)

    evaluations = {
        name: _evaluate(by_corpus, tuple(FEATURE_GROUPS[name]))
        for name in EXPECTED_GROUPS
    }

    degree_values = evaluations["degree_hub"]["graph_values"]
    all_values = evaluations["all"]["graph_values"]
    degree_minus_all = [
        degree_values[graph_id] - all_values[graph_id]
        for graph_id in sorted(all_values)
    ]
    delta_low, delta_high = bootstrap_mean_ci(
        degree_minus_all,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    paired = {
        "mean_degree_hub_minus_all": _mean(degree_minus_all),
        "bootstrap_95_ci": [delta_low, delta_high],
        "degree_hub_better_graphs": sum(value < 0 for value in degree_minus_all),
        "degree_hub_worse_graphs": sum(value > 0 for value in degree_minus_all),
        "ties": sum(value == 0 for value in degree_minus_all),
    }

    return {
        "schema_version": "1.0",
        "protocol": (
            "k=8 five-seed paired feature-representation diagnostic on the "
            "same frozen solver outcomes"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "benchmark_seeds": payload["seeds"],
        "k": payload["k"],
        "graphs": 20,
        "candidate_strategies": payload["candidate_strategies"],
        "evaluations": evaluations,
        "paired_degree_hub_minus_all": paired,
        "interpretation_boundary": [
            "The solver outcomes are identical across all feature groups.",
            "All evaluations use leave-one-corpus-out training and IQR/L2 routing.",
            "This is a post-hoc paired representation diagnostic on the five-seed replication; it does not create an independent solver-outcome sample.",
            "No feature group is promoted to a production/default setting by this analysis.",
            "The degree/hub configuration remains the frozen experimental configuration validated by the preceding prospective replication.",
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
        "all": result["evaluations"]["all"]["mean_relative_regret"],
        "degree_hub": result["evaluations"]["degree_hub"]["mean_relative_regret"],
        "degree_hub_minus_all": result["paired_degree_hub_minus_all"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
