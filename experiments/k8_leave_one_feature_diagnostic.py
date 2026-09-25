from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import FEATURES, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

RESAMPLES = 5000
BOOTSTRAP_SEED = 2024


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _load(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("k") == 8
    assert payload.get("seeds") == [7, 42, 101, 2024, 8191]
    records = payload.get("graph_manifest", [])
    assert len(records) == 20
    by_corpus = defaultdict(list)
    for record in records:
        by_corpus[str(record["corpus"])].append(record)
    assert len(by_corpus) == 4
    return payload, dict(by_corpus)


def _regret(record, selected):
    oracle_cut = float(record["strategy_means"][record["oracle_strategy"]])
    selected_cut = float(record["strategy_means"][selected])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def _evaluate(by_corpus, features):
    values_by_graph = defaultdict(list)
    decisions_by_graph = {}
    for heldout in sorted(by_corpus):
        training = [
            record
            for corpus, records in by_corpus.items()
            if corpus != heldout
            for record in records
        ]
        router = LearnedTopologyRouter(
            features=features,
            scale_mode="iqr",
            metric="l2",
        ).fit(training)
        for record in sorted(by_corpus[heldout], key=lambda x: x["graph_id"]):
            selected = router.predict(record["topology"])
            values_by_graph[record["graph_id"]].append(_regret(record, selected))
            decisions_by_graph[record["graph_id"]] = selected
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
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": [low, high],
        "graph_values": graph_values,
        "decisions": decisions_by_graph,
    }


def run(path: Path):
    payload, by_corpus = _load(path)
    full = tuple(FEATURES)
    baseline = _evaluate(by_corpus, full)
    results = {}
    for feature in FEATURES:
        reduced = tuple(name for name in FEATURES if name != feature)
        result = _evaluate(by_corpus, reduced)
        deltas = [
            result["graph_values"][graph_id] - baseline["graph_values"][graph_id]
            for graph_id in sorted(baseline["graph_values"])
        ]
        low, high = bootstrap_mean_ci(
            deltas,
            resamples=RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
        results[feature] = {
            **result,
            "minus_all_mean": _mean(deltas),
            "minus_all_bootstrap_95_ci": [low, high],
            "changed_graphs": sum(
                baseline["decisions"][g] != result["decisions"][g]
                for g in baseline["decisions"]
            ),
        }

    ranked = sorted(
        results.items(),
        key=lambda item: item[1]["mean_relative_regret"],
    )
    return {
        "schema_version": "1.0",
        "protocol": "k=8 five-seed leave-one-feature-out routing diagnostic",
        "benchmark_commit": payload.get("commit_sha"),
        "k": 8,
        "seeds": payload["seeds"],
        "graphs": 20,
        "all_features": list(FEATURES),
        "all_feature_baseline": baseline,
        "leave_one_feature_out": dict(ranked),
        "interpretation_boundary": [
            "All configurations are evaluated on the same frozen solver outcomes.",
            "Each evaluation uses leave-one-corpus-out training with IQR/L2 routing.",
            "This is a post-hoc feature-isolation diagnostic, not an independent validation sample.",
            "No feature is removed from the public/default router by this analysis.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        name: {
            "mean_relative_regret": data["mean_relative_regret"],
            "minus_all_mean": data["minus_all_mean"],
            "changed_graphs": data["changed_graphs"],
        }
        for name, data in result["leave_one_feature_out"].items()
    }, indent=2))


if __name__ == "__main__":
    main()
