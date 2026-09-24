from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from atof.statistics import bootstrap_mean_ci

from experiments.k4_online_selector import (
    BOOTSTRAP_SEED,
    RESAMPLES,
    SEEDS,
    _fit,
    _load,
    _mean,
    _pairwise_medians,
    _predict_alternate,
)

RANDOM_REPEATS = 500
RANDOM_SEED = 20240924


def _summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_values = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_values.values())
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_graph_value": _mean(values),
        "bootstrap_95_ci": [lower, upper],
        "graph_values": graph_values,
    }


def _relative_regret(selected_cut: float, oracle_cut: float) -> float:
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def run(path: Path) -> dict:
    payload, records = _load(path)
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_corpus[str(record["corpus"])].append(record)

    top1_by_graph: dict[str, list[float]] = defaultdict(list)
    selector_by_graph: dict[str, list[float]] = defaultdict(list)
    alternate_by_graph: dict[str, list[float]] = defaultdict(list)
    selector_probe_graphs_by_fold: dict[str, list[str]] = {}
    alternate_by_unit = {}

    for heldout in sorted(by_corpus):
        training = [
            record
            for corpus, corpus_records in by_corpus.items()
            if corpus != heldout
            for record in corpus_records
        ]
        test = by_corpus[heldout]

        router = _fit(training)
        pair_median, candidate_median, rank_median = _pairwise_medians(
            training,
            router,
        )

        fold_probe_graphs = []
        for record in sorted(test, key=lambda item: item["graph_id"]):
            ranking = router.rank(record["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            probe = predicted_delta < 0.0
            graph_id = record["graph_id"]
            if probe:
                fold_probe_graphs.append(graph_id)

            per_seed_alternate = {}
            for seed in SEEDS:
                seed_values = record["by_seed"].get(seed)
                if seed_values is None:
                    seed_values = record["by_seed"][str(seed)]
                oracle_strategy = min(
                    seed_values,
                    key=lambda strategy: (
                        float(seed_values[strategy]["edge_cut"]),
                        strategy,
                    ),
                )
                oracle_cut = float(seed_values[oracle_strategy]["edge_cut"])
                top1 = ranking[0]
                top1_cut = float(seed_values[top1]["edge_cut"])
                alternate_cut = float(seed_values[alternate]["edge_cut"])

                top1_regret = _relative_regret(top1_cut, oracle_cut)
                alternate_regret = _relative_regret(alternate_cut, oracle_cut)

                top1_by_graph[graph_id].append(top1_regret)
                selector_regret = (
                    min(top1_cut, alternate_cut)
                    if probe
                    else top1_cut
                )
                selector_by_graph[graph_id].append(
                    _relative_regret(selector_regret, oracle_cut)
                )
                alternate_by_graph[graph_id].append(alternate_regret)

                per_seed_alternate[seed] = {
                    "top1_cut": top1_cut,
                    "alternate_cut": alternate_cut,
                }

            alternate_by_unit[graph_id] = {
                "alternate": alternate,
                "predicted_delta": predicted_delta,
                "per_seed": per_seed_alternate,
            }

        selector_probe_graphs_by_fold[heldout] = fold_probe_graphs

    graph_ids = sorted(top1_by_graph)
    probe_graph_count = sum(
        len(graphs) for graphs in selector_probe_graphs_by_fold.values()
    )

    random_means = []
    random_graph_values: list[dict[str, float]] = []

    for repeat in range(RANDOM_REPEATS):
        rng = random.Random(RANDOM_SEED + repeat)
        random_regret_by_graph: dict[str, list[float]] = defaultdict(list)

        for fold, test_records in sorted(by_corpus.items()):
            test_graphs = sorted(
                (record["graph_id"] for record in test_records)
            )
            probe_count = len(selector_probe_graphs_by_fold[str(fold)])
            random_probe = set(
                rng.sample(test_graphs, probe_count)
            )

            for record in test_records:
                graph_id = record["graph_id"]
                use_probe = graph_id in random_probe
                alternate = alternate_by_unit[graph_id]["alternate"]

                for seed in SEEDS:
                    seed_values = record["by_seed"].get(seed)
                    if seed_values is None:
                        seed_values = record["by_seed"][str(seed)]

                    oracle_strategy = min(
                        seed_values,
                        key=lambda strategy: (
                            float(seed_values[strategy]["edge_cut"]),
                            strategy,
                        ),
                    )
                    oracle_cut = float(seed_values[oracle_strategy]["edge_cut"])
                    top1_cut = float(
                        alternate_by_unit[graph_id]["per_seed"][seed]["top1_cut"]
                    )
                    alternate_cut = float(
                        alternate_by_unit[graph_id]["per_seed"][seed]["alternate_cut"]
                    )

                    selected_cut = (
                        min(top1_cut, alternate_cut)
                        if use_probe
                        else top1_cut
                    )
                    random_regret_by_graph[graph_id].append(
                        _relative_regret(selected_cut, oracle_cut)
                    )

        graph_means = {
            graph_id: _mean(random_regret_by_graph[graph_id])
            for graph_id in graph_ids
        }
        random_graph_values.append(graph_means)
        random_means.append(_mean(graph_means.values()))

    selector_graph_means = {
        graph_id: _mean(selector_by_graph[graph_id])
        for graph_id in graph_ids
    }

    selector_vs_random_graph = {
        graph_id: _mean(
            selector_by_graph[graph_id]
        ) - _mean(
            [
                random_values[graph_id]
                for random_values in random_graph_values
            ]
        )
        for graph_id in graph_ids
    }

    lower, upper = bootstrap_mean_ci(
        list(selector_vs_random_graph.values()),
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    random_quantiles = sorted(random_means)
    quantile = lambda q: random_quantiles[
        min(len(random_quantiles) - 1, int(q * len(random_quantiles)))
    ]

    mean_actions = 1.0 + (
        probe_graph_count * len(SEEDS)
    ) / (len(graph_ids) * len(SEEDS))

    return {
        "schema_version": "1.0",
        "protocol": (
            "k=4 budget-matched control for the oracle-free online selector"
        ),
        "benchmark_commit": payload.get("benchmark_commit") or payload.get("commit_sha"),
        "benchmark_head": payload.get("benchmark_head") or payload.get("git_head_sha"),
        "k": 4,
        "seeds": list(SEEDS),
        "graphs": len(graph_ids),
        "seed_units": len(graph_ids) * len(SEEDS),
        "selector": {
            "probe_graph_count": probe_graph_count,
            "probe_graphs": probe_graph_count,
            "probe_graph_rate": probe_graph_count / len(graph_ids),
            "mean_actions": mean_actions,
            "regret": _summary(selector_by_graph),
        },
        "top1": _summary(top1_by_graph),
        "random_control": {
            "repeats": RANDOM_REPEATS,
            "same_probe_graph_count_per_fold": True,
            "mean_actions": mean_actions,
            "mean_graph_regret": _mean(random_means),
            "mean_graph_regret_quantiles": {
                "p05": quantile(0.05),
                "p50": quantile(0.50),
                "p95": quantile(0.95),
            },
        },
        "selector_minus_random_control": {
            "mean": _mean(selector_vs_random_graph.values()),
            "bootstrap_95_ci": [lower, upper],
            "better_graphs": sum(
                value < 0 for value in selector_vs_random_graph.values()
            ),
            "worse_graphs": sum(
                value > 0 for value in selector_vs_random_graph.values()
            ),
            "ties": sum(
                value == 0 for value in selector_vs_random_graph.values()
            ),
        },
        "selector_graph_values": selector_graph_means,
        "random_control_mean_graph_values": {
            graph_id: _mean(
                random_values[graph_id]
                for random_values in random_graph_values
            )
            for graph_id in graph_ids
        },
        "evidence_boundary": [
            "The selector and random control use the same router, the same alternate candidate, and the same total number of probe graphs in every held-out corpus.",
            "Random probe assignment is independent of held-out outcomes and uses a deterministic seed sequence.",
            "Held-out outcomes are evaluation-only.",
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
    print(json.dumps(result["selector_minus_random_control"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
