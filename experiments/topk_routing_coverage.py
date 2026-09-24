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
TOP_K = (1, 2, 3)
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


def _build_records(payload: dict, rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict[int, dict[str, dict[str, float]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in rows:
        grouped[str(row["graph_id"])][int(row["seed"])][str(row["strategy"])] = {
            "edge_cut": float(row["edge_cut"]),
            "runtime_seconds": float(row["runtime_seconds"]),
        }

    records = []
    for graph_id in sorted(grouped):
        seed_rows = grouped[graph_id]
        seed_oracles = []
        for seed in sorted(seed_rows):
            cuts = seed_rows[seed]
            seed_oracles.append(min(cuts, key=lambda name: (cuts[name]["edge_cut"], name)))
        records.append(
            {
                "graph_id": graph_id,
                "corpus": payload["graph_metadata"][graph_id]["corpus"],
                "topology": payload["graph_metadata"][graph_id]["topology"],
                "by_seed": {
                    int(seed): cuts for seed, cuts in sorted(seed_rows.items())
                },
                "seed_oracles": seed_oracles,
                "stable": len(set(seed_oracles)) == 1,
            }
        )
    return records


def _fit(training: list[dict]) -> LearnedTopologyRouter:
    training_rows = [
        {
            "graph": item["graph_id"],
            "topology": item["topology"],
            "oracle_strategy": min(
                {
                    strategy: _mean(
                        [
                            seed_values[strategy]["edge_cut"]
                            for seed_values in item["by_seed"].values()
                        ]
                    )
                    for strategy in next(iter(item["by_seed"].values()))
                },
                key=lambda name: (
                    _mean(
                        [
                            seed_values[name]["edge_cut"]
                            for seed_values in item["by_seed"].values()
                        ]
                    ),
                    name,
                ),
            ),
        }
        for item in training
    ]
    return LearnedTopologyRouter(
        features=FEATURES,
        scale_mode=SCALE_MODE,
        metric=METRIC,
    ).fit(training_rows)


def _summary(values_by_graph: dict[str, list[float]]) -> dict:
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
        "mean_graph_value": _mean(values),
        "bootstrap_95_ci": [lower, upper],
        "graph_values": graph_means,
    }


def _aggregate_metric(
    per_graph: dict[str, list[float]],
) -> dict:
    return _summary(per_graph)


def _stratified(per_graph: dict[str, list[float]], records: list[dict]) -> dict:
    stable_ids = {item["graph_id"] for item in records if item["stable"]}
    unstable_ids = {item["graph_id"] for item in records if not item["stable"]}
    out = {}
    for name, graph_ids in (("stable", stable_ids), ("unstable", unstable_ids)):
        values = {
            graph_id: per_graph[graph_id]
            for graph_id in sorted(graph_ids)
            if graph_id in per_graph
        }
        summary = _summary(values)
        out[name] = {
            "graphs": summary["graphs"],
            "mean_graph_value": summary["mean_graph_value"],
            "bootstrap_95_ci": summary["bootstrap_95_ci"],
        }
    return out


def run(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    corpora = sorted({item["corpus"] for item in records})

    coverage_by_k: dict[int, dict[str, list[float]]] = {
        k: defaultdict(list) for k in TOP_K
    }
    ceiling_regret_by_k: dict[int, dict[str, list[float]]] = {
        k: defaultdict(list) for k in TOP_K
    }
    runtime_by_k: dict[int, dict[str, list[float]]] = {
        k: defaultdict(list) for k in TOP_K
    }
    fold_outputs = []

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)

        fold_coverage = {k: [] for k in TOP_K}
        fold_ceiling = {k: [] for k in TOP_K}
        fold_extra_runtime = {k: [] for k in TOP_K}

        for item in test:
            ranking = router.rank(item["topology"])
            for seed, candidates in sorted(item["by_seed"].items()):
                oracle = min(
                    candidates,
                    key=lambda name: (candidates[name]["edge_cut"], name),
                )
                oracle_cut = candidates[oracle]["edge_cut"]

                for k in TOP_K:
                    selected = ranking[:k]
                    covered = float(oracle in selected)
                    best_cut = min(candidates[name]["edge_cut"] for name in selected)
                    regret = (
                        (best_cut - oracle_cut) / oracle_cut
                        if oracle_cut
                        else 0.0
                    )
                    total_runtime = sum(
                        candidates[name]["runtime_seconds"]
                        for name in selected
                    )

                    coverage_by_k[k][item["graph_id"]].append(covered)
                    ceiling_regret_by_k[k][item["graph_id"]].append(regret)
                    runtime_by_k[k][item["graph_id"]].append(total_runtime)

                    fold_coverage[k].append(covered)
                    fold_ceiling[k].append(regret)
                    if k > 1:
                        fold_extra_runtime[k].append(
                            total_runtime
                            - candidates[ranking[0]]["runtime_seconds"]
                        )

        fold_outputs.append(
            {
                "test_corpus": heldout,
                "test_graphs": len(test),
                "coverage": {
                    str(k): _mean(fold_coverage[k])
                    for k in TOP_K
                },
                "best_of_k_mean_relative_regret": {
                    str(k): _mean(fold_ceiling[k])
                    for k in TOP_K
                },
                "extra_runtime_seconds_mean": {
                    str(k): _mean(fold_extra_runtime[k])
                    for k in TOP_K
                    if k > 1
                },
            }
        )

    aggregate = {"graphs": len(records), "seed_units": len(records) * 3}
    aggregate["coverage"] = {}
    aggregate["best_of_k_ceiling_regret"] = {}
    aggregate["estimated_total_runtime_seconds"] = {}

    for k in TOP_K:
        coverage_summary = _aggregate_metric(coverage_by_k[k])
        regret_summary = _aggregate_metric(ceiling_regret_by_k[k])
        runtime_summary = _aggregate_metric(runtime_by_k[k])

        aggregate["coverage"][str(k)] = {
            "mean_seed_coverage": _mean(
                [value for values in coverage_by_k[k].values() for value in values]
            ),
            "graph_level": coverage_summary,
            "stable_vs_unstable": _stratified(
                coverage_by_k[k], records
            ),
        }
        aggregate["best_of_k_ceiling_regret"][str(k)] = {
            "mean_graph_relative_regret": regret_summary["mean_graph_value"],
            "bootstrap_95_ci": regret_summary["bootstrap_95_ci"],
            "stable_vs_unstable": _stratified(
                ceiling_regret_by_k[k], records
            ),
        }
        aggregate["estimated_total_runtime_seconds"][str(k)] = {
            "mean_graph_total_runtime_seconds": runtime_summary["mean_graph_value"],
            "note": (
                "For k>1 this is the estimated runtime of executing all k "
                "ranked candidates; best-of-k regret is an analysis ceiling "
                "and is not an operational selector."
            ),
        }

    delta_top2 = [
        _mean(ceiling_regret_by_k[2][graph_id])
        - _mean(ceiling_regret_by_k[1][graph_id])
        for graph_id in sorted(ceiling_regret_by_k[1])
    ]
    delta_lower, delta_upper = bootstrap_mean_ci(
        delta_top2,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    aggregate["paired_top2_minus_top1_ceiling"] = {
        "mean": _mean(delta_top2),
        "bootstrap_95_ci": [delta_lower, delta_upper],
        "better_graphs": sum(value < 0 for value in delta_top2),
        "worse_graphs": sum(value > 0 for value in delta_top2),
        "ties": sum(value == 0 for value in delta_top2),
    }

    aggregate["graph_seed_stability"] = {
        item["graph_id"]: {
            "stable": item["stable"],
            "seed_oracles": item["seed_oracles"],
        }
        for item in records
    }

    result = {
        "schema_version": "1.0",
        "protocol": "top-k routing coverage and portfolio ceiling",
        "benchmark_commit": payload.get("commit_sha"),
        "router": {
            "features": list(FEATURES),
            "scale_mode": SCALE_MODE,
            "metric": METRIC,
            "top_k": list(TOP_K),
        },
        "folds": fold_outputs,
        "aggregate": aggregate,
        "evidence_boundary": [
            "The topology ranking is fitted only on training-corpus graph-level mean-oracle labels.",
            "Held-out seed outcomes are never used to produce the ranking.",
            "Coverage is an observable property of the ranked candidate set.",
            "Best-of-k regret is an upper-bound ceiling requiring hindsight selection among the k candidates; it is not a deployable selector.",
            "Executing k candidates increases runtime approximately by their measured runtimes.",
            "No production/default behavior is changed.",
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
