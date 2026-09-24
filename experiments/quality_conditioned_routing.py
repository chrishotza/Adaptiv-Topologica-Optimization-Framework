from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from atof.routing import LearnedTopologyRouter, resolve_features, topology_vector, _feature_scales, _distance
from atof.statistics import bootstrap_mean_ci


FEATURES = resolve_features()
K_NEIGHBORS = 3
EPSILON = 1e-9


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _load_records(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict] = []
    for graph_id, summary in sorted(payload["graph_summaries"].items()):
        if not summary.get("matched"):
            continue
        metadata = payload["graph_metadata"][graph_id]
        edges = max(1, int(metadata["edges"]))
        records.append(
            {
                "graph_id": graph_id,
                "corpus": metadata["corpus"],
                "edges": edges,
                "topology": metadata["topology"],
                "oracle_strategy": str(summary["best_quality"]),
                "strategy_metrics": {
                    strategy: {
                        "edge_cut": float(values["edge_cut"]),
                        "runtime_seconds": float(values["runtime_seconds"]),
                    }
                    for strategy, values in summary["strategies"].items()
                },
            }
        )
    if not records:
        raise ValueError("benchmark contains no matched graph summaries")
    return payload, records


class QualityConditionedRouter:
    """Strategy-specific quality predictor using only training graph outcomes.

    The target is edge_cut / edges, which removes the dominant graph-size
    scale while preserving the partitioning objective. For each strategy,
    prediction is an inverse-distance weighted mean over the k nearest
    training graphs in topology space.
    """

    def __init__(
        self,
        *,
        features: Sequence[str] = FEATURES,
        scale_mode: str = "iqr",
        metric: str = "l2",
        k_neighbors: int = K_NEIGHBORS,
    ) -> None:
        if k_neighbors < 1:
            raise ValueError("k_neighbors must be >= 1")
        self.features = resolve_features(features)
        self.scale_mode = scale_mode
        self.metric = metric
        self.k_neighbors = k_neighbors
        self._scale: tuple[float, ...] = ()
        self._training: tuple[tuple[str, str, tuple[float, ...], float], ...] = ()
        self._strategies: tuple[str, ...] = ()

    def fit(self, training_graphs: Sequence[Mapping]) -> "QualityConditionedRouter":
        if not training_graphs:
            raise ValueError("training_graphs must not be empty")

        vectors = [
            topology_vector(row["topology"], self.features)
            for row in training_graphs
        ]
        self._scale = _feature_scales(vectors, self.scale_mode)
        rows = []
        strategies: set[str] = set()

        for row, vector in zip(training_graphs, vectors):
            edges = max(1, int(row["edges"]))
            for strategy, metrics in row["strategy_metrics"].items():
                strategies.add(str(strategy))
                normalized_cut = float(metrics["edge_cut"]) / edges
                rows.append(
                    (
                        str(row["graph_id"]),
                        str(strategy),
                        vector,
                        normalized_cut,
                    )
                )

        self._training = tuple(rows)
        self._strategies = tuple(sorted(strategies))
        return self

    @property
    def strategies(self) -> tuple[str, ...]:
        return self._strategies

    def predict_scores(self, topology: Mapping) -> dict[str, float]:
        if not self._training:
            raise RuntimeError("router must be fitted before predict_scores()")

        query = topology_vector(topology, self.features)
        distances = [
            (
                _distance(query, vector, self._scale, self.metric),
                graph_id,
                strategy,
                normalized_cut,
            )
            for graph_id, strategy, vector, normalized_cut in self._training
        ]

        result: dict[str, float] = {}
        for strategy in self._strategies:
            neighbors = [
                item for item in distances if item[2] == strategy
            ]
            neighbors.sort(key=lambda item: (item[0], item[1]))
            neighbors = neighbors[: self.k_neighbors]

            exact = [item for item in neighbors if item[0] <= EPSILON]
            if exact:
                result[strategy] = _mean([item[3] for item in exact])
                continue

            weights = [1.0 / max(item[0], EPSILON) for item in neighbors]
            denominator = sum(weights)
            result[strategy] = (
                sum(weight * item[3] for weight, item in zip(weights, neighbors))
                / denominator
            )
        return result

    def rank(self, topology: Mapping) -> tuple[str, ...]:
        scores = self.predict_scores(topology)
        return tuple(
            sorted(
                scores,
                key=lambda strategy: (scores[strategy], strategy),
            )
        )

    def confidence_margin(self, topology: Mapping) -> float:
        scores = self.predict_scores(topology)
        ranked = sorted(scores, key=lambda strategy: (scores[strategy], strategy))
        if len(ranked) < 2:
            return math.inf
        first = scores[ranked[0]]
        second = scores[ranked[1]]
        return (second - first) / abs(first) if first else math.inf


def _fixed_strategy(training: list[dict], mode: str) -> str:
    if mode == "majority":
        counts = defaultdict(int)
        for row in training:
            counts[row["oracle_strategy"]] += 1
        return min(counts, key=lambda strategy: (-counts[strategy], strategy))

    if mode == "global_mean":
        values: dict[str, list[float]] = defaultdict(list)
        for row in training:
            for strategy, metrics in row["strategy_metrics"].items():
                values[strategy].append(float(metrics["edge_cut"]))
        return min(values, key=lambda strategy: (_mean(values[strategy]), strategy))

    raise ValueError(f"unknown control: {mode}")


def _regret(row: Mapping, selected: str) -> float:
    oracle = float(row["strategy_metrics"][row["oracle_strategy"]]["edge_cut"])
    value = float(row["strategy_metrics"][selected]["edge_cut"])
    return (value - oracle) / oracle if oracle else 0.0


def _runtime_ratio(row: Mapping, selected: str) -> float:
    runtimes = sorted(
        float(item["runtime_seconds"])
        for item in row["strategy_metrics"].values()
    )
    median_runtime = runtimes[len(runtimes) // 2]
    selected_runtime = float(row["strategy_metrics"][selected]["runtime_seconds"])
    return selected_runtime / median_runtime if median_runtime else 0.0


def _summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"graphs": 0}
    regrets = [float(row["regret"]) for row in rows]
    runtime_ratios = [float(row["runtime_ratio"]) for row in rows]
    margins = [float(row["confidence_margin"]) for row in rows]
    return {
        "graphs": len(rows),
        "mean_relative_regret": _mean(regrets),
        "median_relative_regret": statistics.median(regrets),
        "mean_runtime_ratio_to_test_median": _mean(runtime_ratios),
        "mean_confidence_margin": _mean(margins),
        "oracle_agreement_rate": sum(
            row["selected_strategy"] == row["oracle_strategy"]
            for row in rows
        ) / len(rows),
    }


def _compare(candidate: list[dict], baseline: list[dict]) -> dict:
    deltas = [
        float(c["regret"]) - float(b["regret"])
        for c, b in zip(candidate, baseline)
    ]
    ci_low, ci_high = bootstrap_mean_ci(deltas, resamples=20000, seed=2026)
    return {
        "mean_delta_regret_candidate_minus_baseline": _mean(deltas),
        "bootstrap_95_ci_delta": [ci_low, ci_high],
        "candidate_better_graphs": sum(delta < 0 for delta in deltas),
        "candidate_worse_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
    }


def run_analysis(
    benchmark_path: str | Path,
    output_path: str | Path,
    *,
    k_neighbors: int = K_NEIGHBORS,
) -> dict:
    benchmark, records = _load_records(Path(benchmark_path))
    corpora = sorted({row["corpus"] for row in records})

    pooled: dict[str, list[dict]] = defaultdict(list)
    folds: dict[str, dict] = {}

    for test_corpus in corpora:
        training = [row for row in records if row["corpus"] != test_corpus]
        testing = [row for row in records if row["corpus"] == test_corpus]
        if not training or not testing:
            continue

        quality_router = QualityConditionedRouter(k_neighbors=k_neighbors).fit(training)
        centroid = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        controls = {
            "majority": _fixed_strategy(training, "majority"),
            "global_mean": _fixed_strategy(training, "global_mean"),
        }

        fold_rows: dict[str, list[dict]] = defaultdict(list)

        for row in testing:
            q_scores = quality_router.predict_scores(row["topology"])
            q_rank = tuple(sorted(q_scores, key=lambda strategy: (q_scores[strategy], strategy)))
            q_selected = q_rank[0]
            q_margin = quality_router.confidence_margin(row["topology"])

            c_selected = centroid.predict(row["topology"])
            c_margin = _centroid_margin(centroid, row["topology"])

            variants = {
                "quality_conditioned": (q_selected, q_margin),
                "centroid": (c_selected, c_margin),
            }
            for name, (selected, margin) in variants.items():
                result = {
                    "graph_id": row["graph_id"],
                    "corpus": test_corpus,
                    "oracle_strategy": row["oracle_strategy"],
                    "selected_strategy": selected,
                    "regret": _regret(row, selected),
                    "runtime_ratio": _runtime_ratio(row, selected),
                    "confidence_margin": margin,
                }
                fold_rows[name].append(result)
                pooled[name].append(result)

            for control_name, strategy in controls.items():
                result = {
                    "graph_id": row["graph_id"],
                    "corpus": test_corpus,
                    "oracle_strategy": row["oracle_strategy"],
                    "selected_strategy": strategy,
                    "regret": _regret(row, strategy),
                    "runtime_ratio": _runtime_ratio(row, strategy),
                    "confidence_margin": math.inf,
                }
                fold_rows[control_name].append(result)
                pooled[control_name].append(result)

        folds[test_corpus] = {
            "graphs": len(testing),
            "controls": controls,
            "summaries": {
                name: _summarize(rows)
                for name, rows in fold_rows.items()
            },
        }

    comparisons = {
        f"quality_conditioned_vs_{baseline}": _compare(
            pooled["quality_conditioned"],
            pooled[baseline],
        )
        for baseline in ("centroid", "majority", "global_mean")
    }

    confidence_buckets: dict[str, list[dict]] = defaultdict(list)
    for row in pooled["quality_conditioned"]:
        margin = float(row["confidence_margin"])
        if margin < 0.01:
            bucket = "lt_1pct"
        elif margin < 0.05:
            bucket = "1pct_to_5pct"
        elif margin < 0.10:
            bucket = "5pct_to_10pct"
        else:
            bucket = "ge_10pct"
        confidence_buckets[bucket].append(row)

    payload = {
        "schema_version": "1.0",
        "protocol": (
            "leave-one-corpus-out topology-conditioned strategy quality routing"
        ),
        "unit_of_analysis": "graph",
        "source_benchmark": str(benchmark_path),
        "source_commit": benchmark.get("commit_sha"),
        "candidate_strategies": benchmark["candidate_strategies"],
        "matched_graphs": len(records),
        "router": {
            "family": "inverse-distance strategy-specific quality predictor",
            "scale_mode": "iqr",
            "metric": "l2",
            "k_neighbors": k_neighbors,
            "target": "edge_cut / edge_count",
        },
        "controls": ["centroid", "majority", "global_mean"],
        "folds": folds,
        "pooled_summaries": {
            name: _summarize(rows)
            for name, rows in pooled.items()
        },
        "paired_comparisons": comparisons,
        "confidence_buckets": {
            bucket: _summarize(rows)
            for bucket, rows in sorted(confidence_buckets.items())
        },
        "evidence_boundary": [
            "All topology scaling, neighbor selection, and strategy-quality estimates use training corpora only.",
            "The held-out corpus is never used to fit the quality predictor.",
            "The target is normalized edge cut; no runtime or oracle label is used as a predictor feature.",
            "This is a research-only router evaluation and does not change the public/default ATOF router.",
        ],
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _centroid_margin(router: LearnedTopologyRouter, topology: Mapping) -> float:
    scores = {}
    vector = topology_vector(topology, router.features)
    for strategy in router.strategies:
        scores[strategy] = _distance(
            vector,
            router._centroids[strategy],
            router._scale,
            router.metric,
        )
    ranked = sorted(scores, key=lambda strategy: (scores[strategy], strategy))
    if len(ranked) < 2:
        return math.inf
    first = scores[ranked[0]]
    second = scores[ranked[1]]
    return (second - first) / first if first else math.inf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/quality_conditioned_routing_latest.json"),
    )
    parser.add_argument(
        "--k-neighbors",
        type=int,
        default=K_NEIGHBORS,
    )
    args = parser.parse_args()
    payload = run_analysis(
        args.benchmark,
        args.output,
        k_neighbors=args.k_neighbors,
    )
    print(json.dumps(payload["pooled_summaries"], indent=2))
    print(json.dumps(payload["paired_comparisons"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
