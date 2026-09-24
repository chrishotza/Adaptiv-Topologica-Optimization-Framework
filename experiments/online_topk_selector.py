from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from experiments.topk_routing_coverage import (
    TOP_K,
    _build_records,
    _fit,
    _load,
    _mean,
)
from atof.statistics import bootstrap_mean_ci

RESAMPLES = 5000
BOOTSTRAP_SEED = 2024
ALTERNATE_RANKS = (1, 2)


def _training_pairwise_medians(training: list[dict], router) -> tuple[dict, dict, dict]:
    pair_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    candidate_values: dict[str, list[float]] = defaultdict(list)
    rank_values: dict[int, list[float]] = defaultdict(list)

    for item in training:
        ranking = router.rank(item["topology"])
        if len(ranking) < 3:
            continue
        for candidates in item["by_seed"].values():
            top1 = ranking[0]
            top1_cut = candidates[top1]["edge_cut"]
            if top1_cut <= 0:
                continue
            for rank in ALTERNATE_RANKS:
                candidate = ranking[rank]
                relative_delta = (
                    candidates[candidate]["edge_cut"] - top1_cut
                ) / top1_cut
                pair_values[(top1, candidate)].append(relative_delta)
                candidate_values[candidate].append(relative_delta)
                rank_values[rank].append(relative_delta)

    pair_median = {
        key: _mean(sorted(values)[len(values) // 2 : len(values) // 2 + 1])
        for key, values in pair_values.items()
        if values
    }
    candidate_median = {
        key: _mean(sorted(values)[len(values) // 2 : len(values) // 2 + 1])
        for key, values in candidate_values.items()
        if values
    }
    rank_median = {
        key: _mean(sorted(values)[len(values) // 2 : len(values) // 2 + 1])
        for key, values in rank_values.items()
        if values
    }
    return pair_median, candidate_median, rank_median


def _predict_alternate(
    ranking: tuple[str, ...],
    *,
    pair_median: dict[tuple[str, str], float],
    candidate_median: dict[str, float],
    rank_median: dict[int, float],
) -> tuple[str, float]:
    top1 = ranking[0]
    candidates = []
    for rank in ALTERNATE_RANKS:
        candidate = ranking[rank]
        prediction = pair_median.get(
            (top1, candidate),
            candidate_median.get(candidate, rank_median.get(rank, 0.0)),
        )
        candidates.append((prediction, rank, candidate))
    return min(candidates, key=lambda item: (item[0], item[1], item[2]))[2:]


def _summary(values_by_graph: dict[str, list[float]]) -> dict:
    graph_means = {
        graph_id: _mean(values)
        for graph_id, values in sorted(values_by_graph.items())
    }
    values = list(graph_means.values())
    if not values:
        return {
            "graphs": 0,
            "mean_graph_value": None,
            "bootstrap_95_ci": None,
            "graph_values": {},
        }
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


def _stratified(values_by_graph: dict[str, list[float]], records: list[dict]) -> dict:
    stable_ids = {item["graph_id"] for item in records if item["stable"]}
    unstable_ids = {item["graph_id"] for item in records if not item["stable"]}
    out = {}
    for name, graph_ids in (("stable", stable_ids), ("unstable", unstable_ids)):
        subset = {
            graph_id: values_by_graph[graph_id]
            for graph_id in sorted(graph_ids)
            if graph_id in values_by_graph
        }
        summary = _summary(subset)
        out[name] = {
            "graphs": summary["graphs"],
            "mean_graph_value": summary["mean_graph_value"],
            "bootstrap_95_ci": summary["bootstrap_95_ci"],
        }
    return out


def _evaluate(path: Path) -> dict:
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    corpora = sorted({item["corpus"] for item in records})

    top1_regret: dict[str, list[float]] = defaultdict(list)
    selector_regret: dict[str, list[float]] = defaultdict(list)
    top2_ceiling: dict[str, list[float]] = defaultdict(list)
    top3_ceiling: dict[str, list[float]] = defaultdict(list)
    selector_runtime: dict[str, list[float]] = defaultdict(list)
    probe_flags: list[int] = []
    action_counts: list[int] = []
    oracle_hits: list[int] = []

    fold_outputs = []

    for heldout in corpora:
        training = [item for item in records if item["corpus"] != heldout]
        test = [item for item in records if item["corpus"] == heldout]
        router = _fit(training)
        pair_median, candidate_median, rank_median = _training_pairwise_medians(
            training, router
        )

        fold_selector_regret = []
        fold_top1_regret = []
        fold_top2 = []
        fold_top3 = []
        fold_runtime = []
        fold_probes = []

        for item in test:
            ranking = router.rank(item["topology"])
            alternate, predicted_delta = _predict_alternate(
                ranking,
                pair_median=pair_median,
                candidate_median=candidate_median,
                rank_median=rank_median,
            )
            probe = predicted_delta < 0.0

            for seed, candidates in sorted(item["by_seed"].items()):
                oracle = min(
                    candidates,
                    key=lambda name: (candidates[name]["edge_cut"], name),
                )
                oracle_cut = candidates[oracle]["edge_cut"]

                top1 = ranking[0]
                top1_cut = candidates[top1]["edge_cut"]
                top2_cut = min(
                    candidates[ranking[0]]["edge_cut"],
                    candidates[ranking[1]]["edge_cut"],
                )
                top3_cut = min(
                    candidates[ranking[0]]["edge_cut"],
                    candidates[ranking[1]]["edge_cut"],
                    candidates[ranking[2]]["edge_cut"],
                )

                if probe:
                    selected_cut = min(
                        top1_cut,
                        candidates[alternate]["edge_cut"],
                    )
                    total_runtime = (
                        candidates[top1]["runtime_seconds"]
                        + candidates[alternate]["runtime_seconds"]
                    )
                    action_count = 2
                else:
                    selected_cut = top1_cut
                    total_runtime = candidates[top1]["runtime_seconds"]
                    action_count = 1

                top1_value = (
                    (top1_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                selector_value = (
                    (selected_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                top2_value = (
                    (top2_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )
                top3_value = (
                    (top3_cut - oracle_cut) / oracle_cut
                    if oracle_cut
                    else 0.0
                )

                top1_regret[item["graph_id"]].append(top1_value)
                selector_regret[item["graph_id"]].append(selector_value)
                top2_ceiling[item["graph_id"]].append(top2_value)
                top3_ceiling[item["graph_id"]].append(top3_value)
                selector_runtime[item["graph_id"]].append(total_runtime)
                probe_flags.append(int(probe))
                action_counts.append(action_count)
                oracle_hits.append(
                    int(
                        oracle == top1
                        or (probe and oracle == alternate)
                    )
                )

                fold_top1_regret.append(top1_value)
                fold_selector_regret.append(selector_value)
                fold_top2.append(top2_value)
                fold_top3.append(top3_value)
                fold_runtime.append(total_runtime)
                fold_probes.append(int(probe))

        fold_outputs.append(
            {
                "test_corpus": heldout,
                "test_graphs": len(test),
                "top1_mean_relative_regret": _mean(fold_top1_regret),
                "selector_mean_relative_regret": _mean(fold_selector_regret),
                "best_of_2_ceiling_mean_relative_regret": _mean(fold_top2),
                "best_of_3_ceiling_mean_relative_regret": _mean(fold_top3),
                "selector_mean_runtime_seconds": _mean(fold_runtime),
                "probe_rate": _mean(fold_probes),
            }
        )

    top1_summary = _summary(top1_regret)
    selector_summary = _summary(selector_regret)
    top2_summary = _summary(top2_ceiling)
    top3_summary = _summary(top3_ceiling)
    runtime_summary = _summary(selector_runtime)

    paired_delta = [
        _mean(selector_regret[graph_id]) - _mean(top1_regret[graph_id])
        for graph_id in sorted(top1_regret)
    ]
    delta_lower, delta_upper = bootstrap_mean_ci(
        paired_delta,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )

    return {
        "schema_version": "1.0",
        "protocol": "oracle-free online selection from topology-ranked top-k candidates",
        "benchmark_commit": payload.get("commit_sha"),
        "router": {
            "training": "leave-one-corpus-out topology centroid router, graph-level mean-oracle labels only",
            "features": "frozen all-topology feature set, IQR scaling, L2 distance",
        },
        "selector": {
            "policy": (
                "Run the topology rank-1 strategy. Using training-fold outcomes only, "
                "estimate the median relative edge-cut delta for the rank-2 and rank-3 "
                "candidates, conditioned first on the ordered (rank-1, candidate) pair "
                "with candidate/rank fallbacks. Probe one alternate only when its "
                "predicted relative delta is strictly negative. After the probe, keep "
                "the lower of the two observed edge cuts."
            ),
            "alternate_ranks": list(ALTERNATE_RANKS),
            "maximum_actions": 2,
            "heldout_oracle_used_for_probe_decision": False,
        },
        "aggregate": {
            "graphs": len(records),
            "seed_units": len(records) * 3,
            "top1": top1_summary,
            "selector": {
                **selector_summary,
                "stable_vs_unstable": _stratified(selector_regret, records),
            },
            "best_of_2_ceiling": top2_summary,
            "best_of_3_ceiling": top3_summary,
            "selector_runtime": runtime_summary,
            "probe_rate": _mean(probe_flags),
            "mean_actions": _mean(action_counts),
            "oracle_hit_rate": _mean(oracle_hits),
            "paired_selector_minus_top1": {
                "mean": _mean(paired_delta),
                "bootstrap_95_ci": [delta_lower, delta_upper],
                "better_graphs": sum(value < 0 for value in paired_delta),
                "worse_graphs": sum(value > 0 for value in paired_delta),
                "ties": sum(value == 0 for value in paired_delta),
            },
        },
        "folds": fold_outputs,
        "evidence_boundary": [
            "The probe decision is generated only from training-fold outcomes and the frozen topology ranking.",
            "Held-out per-seed oracle labels are used only for final evaluation, never for probe selection.",
            "The selector executes at most two full candidate strategies per seed.",
            "Best-of-2 and best-of-3 are hindsight ceilings and are not deployable selectors.",
            "No public/default ATOF behavior is changed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = _evaluate(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
