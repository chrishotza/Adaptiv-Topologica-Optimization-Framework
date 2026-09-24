from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

K = 4
SEEDS = (7, 42, 101, 2024, 8191)
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
ALTERNATE_RANKS = (1, 2)
RESAMPLES = 5000
BOOTSTRAP_SEED = 2024


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _load(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise ValueError("unexpected k=4 benchmark schema")
    if payload.get("k") != K:
        raise ValueError("expected k=4 benchmark")
    if payload.get("seeds") != list(SEEDS):
        raise ValueError(f"expected five-seed manifest {list(SEEDS)}")
    if len(payload.get("candidate_strategies", [])) != 8:
        raise ValueError("expected eight k=4 candidate strategies")

    records = payload.get("graph_manifest")
    if not isinstance(records, list) or len(records) != 20:
        raise ValueError("expected 20 graph records in k=4 graph manifest")

    expected = set(SEEDS)
    for record in records:
        observed = set(record.get("by_seed", {}))
        if observed != {str(seed) for seed in SEEDS} and observed != expected:
            raise ValueError(f"seed manifest mismatch in {record.get('graph_id')}")
        if len(record.get("by_seed", {})) != len(SEEDS):
            raise ValueError(f"incomplete seed record for {record.get('graph_id')}")
        if "oracle_strategy" not in record or "topology" not in record:
            raise ValueError(f"incomplete graph record for {record.get('graph_id')}")
    return payload, records


def _fit(training: list[dict]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in training
    ]
    return LearnedTopologyRouter(
        features=FEATURES,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)


def _pairwise_medians(training: list[dict], router: LearnedTopologyRouter):
    pair_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    candidate_values: dict[str, list[float]] = defaultdict(list)
    rank_values: dict[int, list[float]] = defaultdict(list)

    for record in training:
        ranking = router.rank(record["topology"])
        if len(ranking) < 3:
            continue
        top1 = ranking[0]
        for seed_values in record["by_seed"].values():
            top1_cut = float(seed_values[top1]["edge_cut"])
            if top1_cut <= 0:
                continue
            for rank in ALTERNATE_RANKS:
                candidate = ranking[rank]
                delta = (
                    float(seed_values[candidate]["edge_cut"]) - top1_cut
                ) / top1_cut
                pair_values[(top1, candidate)].append(delta)
                candidate_values[candidate].append(delta)
                rank_values[rank].append(delta)

    def median(values: list[float]) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2.0

    return (
        {key: median(values) for key, values in pair_values.items()},
        {key: median(values) for key, values in candidate_values.items()},
        {key: median(values) for key, values in rank_values.items()},
    )


def _predict_alternate(
    ranking: tuple[str, ...],
    *,
    pair_median: dict[tuple[str, str], float],
    candidate_median: dict[str, float],
    rank_median: dict[int, float],
) -> tuple[str, float]:
    candidates = []
    top1 = ranking[0]
    for rank in ALTERNATE_RANKS:
        candidate = ranking[rank]
        prediction = pair_median.get(
            (top1, candidate),
            candidate_median.get(candidate, rank_median.get(rank, 0.0)),
        )
        candidates.append((float(prediction), rank, candidate))
    if not candidates:
        raise RuntimeError("router returned fewer than three candidates")
    prediction, _, candidate = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    return candidate, prediction


def _oracle_cut(seed_values: dict[str, dict[str, float]]) -> float:
    return min(
        float(metrics["edge_cut"])
        for metrics in seed_values.values()
    )


def _relative_regret(selected_cut: float, oracle_cut: float) -> float:
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def _graph_summary(values_by_graph: dict[str, list[float]]) -> dict:
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


def run(path: Path) -> dict:
    payload, records = _load(path)
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_corpus[str(record["corpus"])].append(record)

    top1_regret: dict[str, list[float]] = defaultdict(list)
    selector_regret: dict[str, list[float]] = defaultdict(list)
    majority_regret: dict[str, list[float]] = defaultdict(list)
    runtime: dict[str, list[float]] = defaultdict(list)
    predicted_by_graph: dict[str, list[float]] = defaultdict(list)
    realized_by_graph: dict[str, list[float]] = defaultdict(list)
    probe_flags: list[int] = []
    action_counts: list[int] = []
    oracle_hits: list[int] = []
    fold_outputs = []

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
        majority = min(
            Counter(record["oracle_strategy"] for record in training),
            key=lambda strategy: (
                -Counter(record["oracle_strategy"] for record in training)[strategy],
                strategy,
            ),
        )

        fold_top1 = []
        fold_selector = []
        fold_majority = []
        fold_probe = []

        for record in test:
            ranking = router.rank(record["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            probe = predicted_delta < 0.0
            top1 = ranking[0]

            for seed in SEEDS:
                seed_values = record["by_seed"].get(seed)
                if seed_values is None:
                    seed_values = record["by_seed"][str(seed)]
                oracle_strategy = min(
                    seed_values,
                    key=lambda name: (
                        float(seed_values[name]["edge_cut"]),
                        name,
                    ),
                )
                oracle_cut = float(seed_values[oracle_strategy]["edge_cut"])
                top1_cut = float(seed_values[top1]["edge_cut"])
                alternate_cut = float(seed_values[alternate]["edge_cut"])
                majority_cut = float(seed_values[majority]["edge_cut"])

                if probe:
                    selected_cut = min(top1_cut, alternate_cut)
                    action = 2
                    selected_runtime = (
                        float(seed_values[top1]["runtime_seconds"])
                        + float(seed_values[alternate]["runtime_seconds"])
                    )
                else:
                    selected_cut = top1_cut
                    action = 1
                    selected_runtime = float(seed_values[top1]["runtime_seconds"])

                top1_value = _relative_regret(top1_cut, oracle_cut)
                selector_value = _relative_regret(selected_cut, oracle_cut)
                majority_value = _relative_regret(majority_cut, oracle_cut)
                realized_delta = _relative_regret(alternate_cut, top1_cut)

                top1_regret[record["graph_id"]].append(top1_value)
                selector_regret[record["graph_id"]].append(selector_value)
                majority_regret[record["graph_id"]].append(majority_value)
                runtime[record["graph_id"]].append(selected_runtime)
                predicted_by_graph[record["graph_id"]].append(predicted_delta)
                realized_by_graph[record["graph_id"]].append(realized_delta)
                probe_flags.append(int(probe))
                action_counts.append(action)
                selected_strategy = top1
                if probe and alternate_cut < top1_cut:
                    selected_strategy = alternate
                oracle_hits.append(int(selected_strategy == oracle_strategy))

                fold_top1.append(top1_value)
                fold_selector.append(selector_value)
                fold_majority.append(majority_value)
                fold_probe.append(int(probe))

        fold_outputs.append(
            {
                "test_corpus": heldout,
                "test_graphs": len(test),
                "top1_mean_relative_regret": _mean(fold_top1),
                "selector_mean_relative_regret": _mean(fold_selector),
                "majority_mean_relative_regret": _mean(fold_majority),
                "probe_rate": _mean(fold_probe),
            }
        )

    graph_ids = sorted(top1_regret)
    top1_summary = _graph_summary(top1_regret)
    selector_summary = _graph_summary(selector_regret)
    majority_summary = _graph_summary(majority_regret)
    runtime_summary = _graph_summary(runtime)

    paired_vs_top1 = [
        _mean(selector_regret[g]) - _mean(top1_regret[g])
        for g in graph_ids
    ]
    paired_vs_majority = [
        _mean(selector_regret[g]) - _mean(majority_regret[g])
        for g in graph_ids
    ]
    top1_vs_majority = [
        _mean(top1_regret[g]) - _mean(majority_regret[g])
        for g in graph_ids
    ]

    top1_low, top1_high = bootstrap_mean_ci(
        paired_vs_top1,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    majority_low, majority_high = bootstrap_mean_ci(
        paired_vs_majority,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    stability = {
        "graphs": len(records),
        "unstable_graphs": sum(
            not record["stable"] for record in records
        ),
        "unstable_graph_rate": _mean(
            [float(not record["stable"]) for record in records]
        ),
        "seed_oracles": {
            record["graph_id"]: record["seed_oracles"]
            for record in records
        },
    }

    prediction_pairs = []
    for graph_id in graph_ids:
        prediction_pairs.extend(
            zip(
                predicted_by_graph[graph_id],
                realized_by_graph[graph_id],
            )
        )
    prediction_errors = [realized - predicted for predicted, realized in prediction_pairs]
    pred_low, pred_high = bootstrap_mean_ci(
        [
            _mean(
                [realized - predicted for predicted, realized in zip(
                    predicted_by_graph[g], realized_by_graph[g]
                )]
            )
            for g in graph_ids
        ],
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    result = {
        "schema_version": "1.0",
        "protocol": (
            "k=4 oracle-free online selector with a five-seed fixed solver grid"
        ),
        "benchmark_commit": payload.get("commit_sha"),
        "benchmark_head": payload.get("git_head_sha"),
        "k": K,
        "seeds": list(SEEDS),
        "candidate_strategies": payload["candidate_strategies"],
        "router": {
            "training": "leave-one-corpus-out topology centroid router with graph-level mean-oracle labels",
            "features": list(FEATURES),
            "scale_mode": "iqr",
            "metric": "l2",
        },
        "selector": {
            "policy": (
                "Run the topology rank-1 strategy. Predict rank-2/rank-3 "
                "relative edge-cut deltas from training-only ordered-pair "
                "medians with candidate/rank fallbacks. Probe one alternate "
                "only when its predicted relative delta is strictly negative."
            ),
            "alternate_ranks": list(ALTERNATE_RANKS),
            "maximum_actions": 2,
            "heldout_oracle_used_for_probe_decision": False,
        },
        "aggregate": {
            "graphs": len(graph_ids),
            "seed_units": len(graph_ids) * len(SEEDS),
            "top1": top1_summary,
            "selector": selector_summary,
            "majority_control": majority_summary,
            "selector_runtime": runtime_summary,
            "probe_rate": _mean(probe_flags),
            "mean_actions": _mean(action_counts),
            "oracle_hit_rate": _mean(oracle_hits),
            "paired_selector_minus_top1": {
                "mean": _mean(paired_vs_top1),
                "bootstrap_95_ci": [top1_low, top1_high],
                "better_graphs": sum(value < 0 for value in paired_vs_top1),
                "worse_graphs": sum(value > 0 for value in paired_vs_top1),
                "ties": sum(value == 0 for value in paired_vs_top1),
            },
            "paired_selector_minus_majority": {
                "mean": _mean(paired_vs_majority),
                "bootstrap_95_ci": [majority_low, majority_high],
                "better_graphs": sum(value < 0 for value in paired_vs_majority),
                "worse_graphs": sum(value > 0 for value in paired_vs_majority),
                "ties": sum(value == 0 for value in paired_vs_majority),
            },
            "paired_top1_minus_majority": {
                "mean": _mean(top1_vs_majority),
                "bootstrap_95_ci": list(bootstrap_mean_ci(
                    top1_vs_majority,
                    resamples=RESAMPLES,
                    seed=BOOTSTRAP_SEED,
                )),
            },
            "prediction": {
                "mean_error_over_seed_pairs": _mean(prediction_errors),
                "mean_absolute_error": _mean(abs(value) for value in prediction_errors),
                "graph_level_bootstrap_95_ci_mean_error": [pred_low, pred_high],
            },
            "seed_stability": stability,
        },
        "folds": fold_outputs,
        "graph_manifest": [
            {
                "graph_id": graph_id,
                "predicted_relative_delta_mean": _mean(predicted_by_graph[graph_id]),
                "realized_relative_delta_mean": _mean(realized_by_graph[graph_id]),
            }
            for graph_id in graph_ids
        ],
        "evidence_boundary": [
            "All predictor fits are leave-one-corpus-out and use training-graph outcomes only.",
            "The held-out oracle is never used to choose the probe or alternate.",
            "The probe executes at most two candidate strategies per seed.",
            "The five solver seeds were fixed before held-out evaluation.",
            "The benchmark candidate set and topology routing configuration are inherited unchanged from the validated k=4 protocol.",
            "No production/default ATOF behavior changes.",
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
