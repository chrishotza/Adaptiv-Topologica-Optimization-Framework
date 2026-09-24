from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

FEATURES = (
    "density",
    "avg_degree",
    "degree_std",
    "hub_ratio",
    "degree_gini",
    "clustering",
    "transitivity",
    "core_number",
    "diameter",
    "avg_path_length",
    "modularity",
)
SCALE_MODE = "iqr"
METRIC = "l2"
BOOTSTRAP_RESAMPLES = 5000
BOOTSTRAP_SEED = 2024


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _load(path: Path) -> tuple[dict, list[dict], list[str], list[int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in payload["rows"] if row.get("status") == "ok"]
    strategies = list(payload["candidate_strategies"])
    seeds = [int(seed) for seed in payload["seeds"]]
    if payload.get("matched_graphs") != 20:
        raise ValueError("expected the frozen 20-graph benchmark")
    if len(rows) != 660:
        raise ValueError("expected exactly 660 successful benchmark rows")
    if len(strategies) != 11 or seeds != [42, 101, 2024]:
        raise ValueError("unexpected strategy/seed manifest")
    return payload, rows, strategies, seeds


def _graph_oracle_rows(rows: list[dict], payload: dict) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["graph_id"])].append(row)

    result = []
    for graph_id in sorted(grouped):
        by_strategy: dict[str, list[float]] = defaultdict(list)
        for row in grouped[graph_id]:
            by_strategy[str(row["strategy"])].append(float(row["edge_cut"]))
        means = {name: _mean(values) for name, values in by_strategy.items()}
        oracle = min(means, key=lambda name: (means[name], name))
        result.append(
            {
                "graph_id": graph_id,
                "corpus": payload["graph_metadata"][graph_id]["corpus"],
                "topology": payload["graph_metadata"][graph_id]["topology"],
                "oracle_strategy": oracle,
            }
        )
    return result


def _seed_oracle_rows(rows: list[dict], payload: dict) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["graph_id"]), int(row["seed"]))].append(row)

    result = []
    for (graph_id, seed), group in sorted(grouped.items()):
        cuts = {str(row["strategy"]): float(row["edge_cut"]) for row in group}
        oracle = min(cuts, key=lambda name: (cuts[name], name))
        result.append(
            {
                "graph_id": graph_id,
                "seed": seed,
                "corpus": payload["graph_metadata"][graph_id]["corpus"],
                "topology": payload["graph_metadata"][graph_id]["topology"],
                "oracle_strategy": oracle,
            }
        )
    return result


def _fit(training: list[dict]) -> LearnedTopologyRouter:
    return LearnedTopologyRouter(
        features=FEATURES,
        scale_mode=SCALE_MODE,
        metric=METRIC,
    ).fit(training)


def _graph_regret_summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_means = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_means.values())
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=BOOTSTRAP_RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_graph_relative_regret": _mean(values),
        "median_graph_relative_regret": sorted(values)[len(values) // 2] if values else 0.0,
        "bootstrap_95_ci": [lower, upper],
        "graph_relative_regret": graph_means,
    }


def _evaluate_fold(
    *,
    train_graphs: list[dict],
    train_seed_units: list[dict],
    test_graphs: list[dict],
    test_seed_units: list[dict],
    rows: list[dict],
    strategies: list[str],
    corpus: str,
) -> dict:
    graph_router = _fit(train_graphs)
    seed_expanded_router = _fit(train_seed_units)
    test_ids = sorted({item["graph_id"] for item in test_graphs})
    topology_by_graph = {item["graph_id"]: item["topology"] for item in test_graphs}

    graph_predictions = {
        graph_id: graph_router.predict(topology_by_graph[graph_id])
        for graph_id in test_ids
    }
    seed_expanded_predictions = {
        graph_id: seed_expanded_router.predict(topology_by_graph[graph_id])
        for graph_id in test_ids
    }

    rows_by_unit: dict[tuple[str, int], dict[str, float]] = {}
    for graph_id in test_ids:
        for row in rows:
            if row["graph_id"] == graph_id:
                rows_by_unit.setdefault((graph_id, int(row["seed"])), {})[
                    str(row["strategy"])
                ] = float(row["edge_cut"])

    graph_router_regret: dict[str, list[float]] = defaultdict(list)
    seed_router_regret: dict[str, list[float]] = defaultdict(list)
    oracle_labels_by_graph: dict[str, set[str]] = defaultdict(set)
    graph_router_seed_agreement: dict[str, list[int]] = defaultdict(list)

    for graph_id in test_ids:
        graph_prediction = graph_predictions[graph_id]
        seed_prediction = seed_expanded_predictions[graph_id]
        units = sorted(
            (key, cuts)
            for key, cuts in rows_by_unit.items()
            if key[0] == graph_id
        )
        for (_, seed), cuts in units:
            seed_oracle = min(cuts, key=lambda name: (cuts[name], name))
            oracle_cut = cuts[seed_oracle]
            graph_cut = cuts[graph_prediction]
            seed_cut = cuts[seed_prediction]
            graph_router_regret[graph_id].append(
                (graph_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
            )
            seed_router_regret[graph_id].append(
                (seed_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
            )
            oracle_labels_by_graph[graph_id].add(seed_oracle)
            graph_router_seed_agreement[graph_id].append(
                int(graph_prediction == seed_oracle)
            )

    graph_summary = _graph_regret_summary(dict(graph_router_regret))
    seed_summary = _graph_regret_summary(dict(seed_router_regret))
    delta_by_graph = {
        graph_id: seed_summary["graph_relative_regret"][graph_id]
        - graph_summary["graph_relative_regret"][graph_id]
        for graph_id in test_ids
    }
    delta_values = list(delta_by_graph.values())
    delta_ci = bootstrap_mean_ci(
        delta_values,
        resamples=BOOTSTRAP_RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    stability = {
        graph_id: {
            "distinct_seed_oracles": len(oracle_labels_by_graph[graph_id]),
            "seed_oracle_strategies": sorted(oracle_labels_by_graph[graph_id]),
            "graph_router_seed_agreement_rate": _mean(
                graph_router_seed_agreement[graph_id]
            ),
        }
        for graph_id in test_ids
    }

    return {
        "test_corpus": corpus,
        "test_graphs": len(test_ids),
        "seed_units": len(test_ids) * 3,
        "graph_router": graph_summary,
        "seed_expanded_router": seed_summary,
        "paired_delta_seed_expanded_minus_graph_router": {
            "mean": _mean(delta_values),
            "bootstrap_95_ci": [delta_ci[0], delta_ci[1]],
            "better_graphs": sum(value < 0 for value in delta_values),
            "worse_graphs": sum(value > 0 for value in delta_values),
            "ties": sum(value == 0 for value in delta_values),
        },
        "seed_oracle_stability": stability,
        "training_graphs": len(train_graphs),
        "training_seed_units": len(train_seed_units),
        "candidate_strategies": len(strategies),
    }


def run(path: Path) -> dict:
    payload, rows, strategies, seeds = _load(path)
    graph_records = _graph_oracle_rows(rows, payload)
    seed_records = _seed_oracle_rows(rows, payload)
    corpora = sorted({item["corpus"] for item in graph_records})

    folds = []
    all_graph_regret: dict[str, float] = {}
    all_seed_regret: dict[str, float] = {}
    all_delta: dict[str, float] = {}
    all_stability: dict[str, dict] = {}

    for heldout in corpora:
        train_graphs = [item for item in graph_records if item["corpus"] != heldout]
        test_graphs = [item for item in graph_records if item["corpus"] == heldout]
        train_seed_units = [item for item in seed_records if item["corpus"] != heldout]
        test_seed_units = [item for item in seed_records if item["corpus"] == heldout]

        fold = _evaluate_fold(
            train_graphs=train_graphs,
            train_seed_units=train_seed_units,
            test_graphs=test_graphs,
            test_seed_units=test_seed_units,
            rows=rows,
            strategies=strategies,
            corpus=heldout,
        )
        folds.append(fold)
        all_graph_regret.update(fold["graph_router"]["graph_relative_regret"])
        all_seed_regret.update(fold["seed_expanded_router"]["graph_relative_regret"])
        for graph_id, value in fold[
            "paired_delta_seed_expanded_minus_graph_router"
        ].items():
            if graph_id in {"mean", "bootstrap_95_ci", "better_graphs", "worse_graphs", "ties"}:
                continue
        for graph_id in fold["graph_router"]["graph_relative_regret"]:
            all_delta[graph_id] = (
                fold["seed_expanded_router"]["graph_relative_regret"][graph_id]
                - fold["graph_router"]["graph_relative_regret"][graph_id]
            )
        all_stability.update(fold["seed_oracle_stability"])

    delta_values = [all_delta[key] for key in sorted(all_delta)]
    delta_ci = bootstrap_mean_ci(
        delta_values,
        resamples=BOOTSTRAP_RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    stability_values = list(all_stability.values())
    unstable = sum(
        item["distinct_seed_oracles"] > 1 for item in stability_values
    )

    result = {
        "schema_version": "1.0",
        "protocol": "cross-seed routing calibration",
        "unit_of_analysis": "graph-level bootstrap over seed-expanded held-out units",
        "benchmark_commit": payload.get("commit_sha"),
        "router": {
            "features": list(FEATURES),
            "scale_mode": SCALE_MODE,
            "metric": METRIC,
        },
        "seeds": seeds,
        "strategies": strategies,
        "corpora": corpora,
        "folds": folds,
        "aggregate": {
            "graphs": len(all_graph_regret),
            "seed_units": len(all_graph_regret) * len(seeds),
            "graph_router_mean_graph_relative_regret": _mean(list(all_graph_regret.values())),
            "seed_expanded_router_mean_graph_relative_regret": _mean(list(all_seed_regret.values())),
            "paired_delta_seed_expanded_minus_graph_router": _mean(delta_values),
            "paired_delta_bootstrap_95_ci": [delta_ci[0], delta_ci[1]],
            "paired_better_graphs": sum(value < 0 for value in delta_values),
            "paired_worse_graphs": sum(value > 0 for value in delta_values),
            "paired_ties": sum(value == 0 for value in delta_values),
            "mean_graph_router_seed_oracle_agreement_rate": _mean(
                [item["graph_router_seed_agreement_rate"] for item in stability_values]
            ),
            "graphs_with_multiple_seed_oracles": unstable,
            "fraction_graphs_with_multiple_seed_oracles": (
                unstable / len(stability_values) if stability_values else 0.0
            ),
            "oracle_stability": all_stability,
        },
        "evidence_boundary": [
            "All three seeds of each held-out graph are excluded from training.",
            "The seed-expanded router uses seed-level oracle labels only on training graphs.",
            "The held-out predictor observes topology only and does not receive the seed as an input.",
            "Bootstrap intervals operate on graph-level aggregates to avoid treating repeated seeds as independent graphs.",
            "This calibrates seed sensitivity and router stability; it is not a solver-superiority claim.",
            "No production/default policy is changed.",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
