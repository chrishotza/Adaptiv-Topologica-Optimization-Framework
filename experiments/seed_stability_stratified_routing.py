from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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
RESAMPLES = 5000
BOOTSTRAP_SEED = 2024


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _load(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in payload["rows"] if row.get("status") == "ok"]
    if payload.get("matched_graphs") != 20:
        raise ValueError("expected 20 matched graphs")
    if len(payload.get("candidate_strategies", [])) != 11:
        raise ValueError("expected 11 strategies")
    if payload.get("seeds") != [42, 101, 2024]:
        raise ValueError("unexpected seed manifest")
    if len(rows) != 660:
        raise ValueError("expected exactly 660 successful rows")
    return payload, rows


def _records(payload: dict, rows: list[dict]) -> list[dict]:
    by_graph: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_graph[str(row["graph_id"])].append(row)

    result = []
    for graph_id, group in sorted(by_graph.items()):
        by_seed: dict[int, dict[str, float]] = defaultdict(dict)
        for row in group:
            by_seed[int(row["seed"])][str(row["strategy"])] = float(row["edge_cut"])

        seed_oracles = [
            min(cuts, key=lambda name: (cuts[name], name))
            for _, cuts in sorted(by_seed.items())
        ]
        mean_cuts: dict[str, list[float]] = defaultdict(list)
        for cuts in by_seed.values():
            for strategy, cut in cuts.items():
                mean_cuts[strategy].append(cut)
        mean_cuts = {
            strategy: _mean(values) for strategy, values in mean_cuts.items()
        }
        mean_oracle = min(mean_cuts, key=lambda name: (mean_cuts[name], name))
        counts = Counter(seed_oracles)
        max_frequency = max(counts.values())
        modal_oracle = min(
            (strategy for strategy, count in counts.items() if count == max_frequency)
        )
        result.append(
            {
                "graph_id": graph_id,
                "corpus": payload["graph_metadata"][graph_id]["corpus"],
                "topology": payload["graph_metadata"][graph_id]["topology"],
                "mean_oracle": mean_oracle,
                "modal_oracle": modal_oracle,
                "seed_oracles": seed_oracles,
                "distinct_seed_oracles": len(counts),
                "oracle_concentration": max_frequency / len(seed_oracles),
                "by_seed": {
                    seed: cuts for seed, cuts in sorted(by_seed.items())
                },
            }
        )
    return result


def _fit(label_field: str, training: list[dict]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": item["graph_id"],
            "topology": item["topology"],
            "oracle_strategy": item[label_field],
        }
        for item in training
    ]
    return LearnedTopologyRouter(
        features=FEATURES,
        scale_mode=SCALE_MODE,
        metric=METRIC,
    ).fit(rows)


def _graph_summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_means = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_means.values())
    lower, upper = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_graph_relative_regret": _mean(values),
        "bootstrap_95_ci": [lower, upper],
        "graph_relative_regret": graph_means,
    }


def _evaluate(
    training: list[dict],
    test: list[dict],
    label_field: str,
) -> tuple[dict, dict[str, dict]]:
    router = _fit(label_field, training)
    regret_by_graph: dict[str, list[float]] = defaultdict(list)
    agreement_by_graph: dict[str, list[int]] = defaultdict(list)
    metadata: dict[str, dict] = {}

    for item in test:
        graph_id = item["graph_id"]
        prediction = router.predict(item["topology"])
        for seed, cuts in sorted(item["by_seed"].items()):
            oracle = min(cuts, key=lambda name: (cuts[name], name))
            oracle_cut = cuts[oracle]
            selected_cut = cuts[prediction]
            regret_by_graph[graph_id].append(
                (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
            )
            agreement_by_graph[graph_id].append(int(prediction == oracle))
        metadata[graph_id] = {
            "prediction": prediction,
            "distinct_seed_oracles": item["distinct_seed_oracles"],
            "oracle_concentration": item["oracle_concentration"],
        }

    return _graph_summary(dict(regret_by_graph)), {
        graph_id: {
            **metadata[graph_id],
            "mean_seed_oracle_agreement": _mean(agreement_by_graph[graph_id]),
            "regret": _mean(regret_by_graph[graph_id]),
        }
        for graph_id in sorted(metadata)
    }


def _stratify(
    details: dict[str, dict],
    stable: bool,
) -> dict:
    selected = {
        graph_id: item
        for graph_id, item in details.items()
        if (item["distinct_seed_oracles"] == 1) == stable
    }
    values = [item["regret"] for item in selected.values()]
    agreements = [item["mean_seed_oracle_agreement"] for item in selected.values()]
    if not values:
        return {"graphs": 0, "mean_graph_relative_regret": 0.0, "mean_seed_oracle_agreement": 0.0}
    lower, upper = bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
    return {
        "graphs": len(values),
        "mean_graph_relative_regret": _mean(values),
        "bootstrap_95_ci": [lower, upper],
        "mean_seed_oracle_agreement": _mean(agreements),
        "graphs": len(values),
    }


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _records(payload, rows)
    corpora = sorted({item["corpus"] for item in records})

    folds = []
    all_mean_details: dict[str, dict] = {}
    all_modal_details: dict[str, dict] = {}

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        mean_summary, mean_details = _evaluate(training, test, "mean_oracle")
        modal_summary, modal_details = _evaluate(training, test, "modal_oracle")
        all_mean_details.update(mean_details)
        all_modal_details.update(modal_details)

        delta = [
            modal_details[g]["regret"] - mean_details[g]["regret"]
            for g in sorted(mean_details)
        ]
        lower, upper = bootstrap_mean_ci(delta, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
        folds.append(
            {
                "test_corpus": heldout,
                "test_graphs": len(test),
                "mean_oracle_router": mean_summary,
                "modal_oracle_router": modal_summary,
                "paired_delta_modal_minus_mean": {
                    "mean": _mean(delta),
                    "bootstrap_95_ci": [lower, upper],
                    "better_graphs": sum(v < 0 for v in delta),
                    "worse_graphs": sum(v > 0 for v in delta),
                    "ties": sum(v == 0 for v in delta),
                },
            }
        )

    mean_values = [all_mean_details[g]["regret"] for g in sorted(all_mean_details)]
    modal_values = [all_modal_details[g]["regret"] for g in sorted(all_modal_details)]
    delta_values = [
        all_modal_details[g]["regret"] - all_mean_details[g]["regret"]
        for g in sorted(all_mean_details)
    ]
    delta_lower, delta_upper = bootstrap_mean_ci(
        delta_values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    result = {
        "schema_version": "1.0",
        "protocol": "seed-stability stratified routing calibration",
        "benchmark_commit": payload.get("commit_sha"),
        "router": {
            "features": list(FEATURES),
            "scale_mode": SCALE_MODE,
            "metric": METRIC,
        },
        "seeds": payload["seeds"],
        "folds": folds,
        "aggregate": {
            "graphs": len(records),
            "mean_oracle_router_mean_graph_relative_regret": _mean(mean_values),
            "modal_oracle_router_mean_graph_relative_regret": _mean(modal_values),
            "paired_delta_modal_minus_mean": _mean(delta_values),
            "paired_delta_bootstrap_95_ci": [delta_lower, delta_upper],
            "paired_better_graphs": sum(v < 0 for v in delta_values),
            "paired_worse_graphs": sum(v > 0 for v in delta_values),
            "paired_ties": sum(v == 0 for v in delta_values),
            "stable_graphs": sum(item["distinct_seed_oracles"] == 1 for item in records),
            "unstable_graphs": sum(item["distinct_seed_oracles"] > 1 for item in records),
            "mean_oracle_router_stable": _stratify(all_mean_details, True),
            "mean_oracle_router_unstable": _stratify(all_mean_details, False),
            "modal_oracle_router_stable": _stratify(all_modal_details, True),
            "modal_oracle_router_unstable": _stratify(all_modal_details, False),
            "graph_seed_stability": {
                item["graph_id"]: {
                    "distinct_seed_oracles": item["distinct_seed_oracles"],
                    "oracle_concentration": item["oracle_concentration"],
                    "seed_oracles": item["seed_oracles"],
                }
                for item in records
            },
        },
        "evidence_boundary": [
            "Both target definitions are derived only from training graphs in each corpus fold.",
            "Held-out evaluation is performed against every held-out seed oracle.",
            "Stable means one oracle strategy across all three seeds; unstable means at least two.",
            "This is a target-definition and stratification study, not a production-policy selection.",
            "No public/default behavior is changed.",
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
