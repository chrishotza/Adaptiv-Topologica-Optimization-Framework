from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping, Sequence

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

FEATURE_GROUPS = {
    "all": FEATURES,
    "degree_hub": (
        "density",
        "avg_degree",
        "degree_std",
        "hub_ratio",
        "degree_gini",
    ),
    "mesoscopic": (
        "clustering",
        "transitivity",
        "modularity",
    ),
    "global_paths": (
        "core_number",
        "diameter",
        "avg_path_length",
    ),
}

FEATURE_ABLATIONS = {
    "all": FEATURES,
    "without_degree_hub": tuple(
        feature for feature in FEATURES if feature not in FEATURE_GROUPS["degree_hub"]
    ),
    "without_mesoscopic": tuple(
        feature for feature in FEATURES if feature not in FEATURE_GROUPS["mesoscopic"]
    ),
    "without_global_paths": tuple(
        feature for feature in FEATURES if feature not in FEATURE_GROUPS["global_paths"]
    ),
}


def resolve_features(features: Sequence[str] | None = None) -> tuple[str, ...]:
    """Validate and normalize an explicit topology-feature subset."""
    selected = FEATURES if features is None else tuple(features)
    if not selected:
        raise ValueError("features must contain at least one topology feature")
    unknown = sorted(set(selected).difference(FEATURES))
    if unknown:
        raise ValueError(
            "unknown topology features: " + ", ".join(unknown)
        )
    if len(set(selected)) != len(selected):
        raise ValueError("features must not contain duplicates")
    return selected


def topology_vector(
    profile: Mapping,
    features: Sequence[str] | None = None,
) -> tuple[float, ...]:
    """Convert a topology profile into a finite vector for selected features."""
    values: list[float] = []
    for name in resolve_features(features):
        value = profile.get(name, 0.0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        if value != value:
            value = 0.0
        values.append(value)
    return tuple(values)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _distance(a: Sequence[float], b: Sequence[float], scale: Sequence[float]) -> float:
    return sqrt(
        sum(((x - y) / s) ** 2 for x, y, s in zip(a, b, scale) if s > 0)
    )


@dataclass(frozen=True)
class RoutingEvaluation:
    graph: str
    selected_strategy: str
    oracle_strategy: str
    selected_mean_edge_cut: float
    oracle_mean_edge_cut: float
    absolute_regret: float
    relative_regret: float

    def to_dict(self) -> dict:
        return {
            "graph": self.graph,
            "selected_strategy": self.selected_strategy,
            "oracle_strategy": self.oracle_strategy,
            "selected_mean_edge_cut": self.selected_mean_edge_cut,
            "oracle_mean_edge_cut": self.oracle_mean_edge_cut,
            "absolute_regret": self.absolute_regret,
            "relative_regret": self.relative_regret,
        }


class LearnedTopologyRouter:
    """Centroid router trained on graph-level oracle labels."""

    def __init__(self, features: Sequence[str] | None = None) -> None:
        self.features = resolve_features(features)
        self._centroids: dict[str, tuple[float, ...]] = {}
        self._scale: tuple[float, ...] = ()

    @property
    def strategies(self) -> tuple[str, ...]:
        return tuple(sorted(self._centroids))

    def fit(self, training_graphs: Sequence[Mapping]) -> "LearnedTopologyRouter":
        if not training_graphs:
            raise ValueError("training_graphs must not be empty")

        vectors = [
            topology_vector(row["topology"], self.features)
            for row in training_graphs
        ]
        width = len(vectors[0])

        mins = [min(vector[i] for vector in vectors) for i in range(width)]
        maxs = [max(vector[i] for vector in vectors) for i in range(width)]
        scale = [maxs[i] - mins[i] for i in range(width)]
        scale = [value if value > 0 else 1.0 for value in scale]

        groups: dict[str, list[tuple[float, ...]]] = defaultdict(list)
        for row, vector in zip(training_graphs, vectors):
            groups[str(row["oracle_strategy"])].append(vector)

        if not groups:
            raise ValueError("training_graphs contain no oracle_strategy labels")

        self._scale = tuple(scale)
        self._centroids = {
            strategy: tuple(
                _mean(vector[i] for vector in vectors_for_strategy)
                for i in range(width)
            )
            for strategy, vectors_for_strategy in groups.items()
        }
        return self

    def predict(self, topology: Mapping) -> str:
        if not self._centroids:
            raise RuntimeError("router must be fitted before predict()")

        vector = topology_vector(topology, self.features)
        return min(
            self._centroids,
            key=lambda strategy: (
                _distance(vector, self._centroids[strategy], self._scale),
                strategy,
            ),
        )


class NearestTopologyRouter:
    """1-nearest-neighbor router in standardized topology-feature space."""

    def __init__(self, features: Sequence[str] | None = None) -> None:
        self.features = resolve_features(features)
        self._training: tuple[tuple[str, str, tuple[float, ...]], ...] = ()
        self._scale: tuple[float, ...] = ()

    @property
    def strategies(self) -> tuple[str, ...]:
        return tuple(sorted({item[1] for item in self._training}))

    def fit(self, training_graphs: Sequence[Mapping]) -> "NearestTopologyRouter":
        if not training_graphs:
            raise ValueError("training_graphs must not be empty")

        vectors = [
            topology_vector(row["topology"], self.features)
            for row in training_graphs
        ]
        width = len(vectors[0])
        mins = [min(vector[i] for vector in vectors) for i in range(width)]
        maxs = [max(vector[i] for vector in vectors) for i in range(width)]
        scale = [maxs[i] - mins[i] for i in range(width)]
        scale = [value if value > 0 else 1.0 for value in scale]

        self._scale = tuple(scale)
        self._training = tuple(
            sorted(
                (
                    str(row.get("graph", "")),
                    str(row["oracle_strategy"]),
                    vector,
                )
                for row, vector in zip(training_graphs, vectors)
            )
        )
        return self

    def predict(self, topology: Mapping) -> str:
        if not self._training:
            raise RuntimeError("router must be fitted before predict()")

        vector = topology_vector(topology, self.features)
        graph, strategy, _ = min(
            self._training,
            key=lambda item: (
                _distance(vector, item[2], self._scale),
                item[1],
                item[0],
            ),
        )
        del graph
        return strategy


def graph_oracle(rows: Iterable[Mapping]) -> dict[str, str]:
    """Compute one oracle strategy per graph from its available seeds."""
    grouped: dict[str, list[Mapping]] = defaultdict(list)
    for row in rows:
        grouped[str(row["graph"])].append(row)

    result: dict[str, str] = {}
    for graph, group in grouped.items():
        by_strategy: dict[str, list[float]] = defaultdict(list)
        for row in group:
            by_strategy[str(row["strategy"])].append(float(row["edge_cut"]))

        means = {
            strategy: _mean(values) for strategy, values in by_strategy.items()
        }
        result[graph] = min(means, key=lambda strategy: (means[strategy], strategy))
    return result


def global_strategy_oracle(rows: Iterable[Mapping]) -> str:
    """Choose one fixed strategy using only the supplied training graphs."""
    by_strategy: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_strategy[str(row["strategy"])].append(float(row["edge_cut"]))

    if not by_strategy:
        raise ValueError("rows must contain at least one strategy result")

    means = {
        strategy: _mean(values) for strategy, values in by_strategy.items()
    }
    return min(means, key=lambda strategy: (means[strategy], strategy))


def evaluate_holdout_predictions(
    rows: Iterable[Mapping],
    predictions: Mapping[str, str],
) -> list[RoutingEvaluation]:
    """Evaluate held-out graph predictions against graph-level oracles."""
    grouped: dict[str, list[Mapping]] = defaultdict(list)
    for row in rows:
        grouped[str(row["graph"])].append(row)

    evaluations: list[RoutingEvaluation] = []
    for graph, group in sorted(grouped.items()):
        selected = predictions[graph]
        by_strategy: dict[str, list[float]] = defaultdict(list)
        for row in group:
            by_strategy[str(row["strategy"])].append(float(row["edge_cut"]))

        means = {strategy: _mean(values) for strategy, values in by_strategy.items()}
        oracle = min(means, key=lambda strategy: (means[strategy], strategy))
        selected_mean = means[selected]
        oracle_mean = means[oracle]
        regret = selected_mean - oracle_mean

        evaluations.append(
            RoutingEvaluation(
                graph=graph,
                selected_strategy=selected,
                oracle_strategy=oracle,
                selected_mean_edge_cut=selected_mean,
                oracle_mean_edge_cut=oracle_mean,
                absolute_regret=regret,
                relative_regret=regret / oracle_mean if oracle_mean else 0.0,
            )
        )
    return evaluations


def routing_summary(evaluations: Iterable[RoutingEvaluation]) -> dict:
    """Aggregate graph-level routing performance."""
    evaluations = list(evaluations)
    if not evaluations:
        return {
            "graphs": 0,
            "oracle_agreement_rate": 0.0,
            "mean_absolute_regret": 0.0,
            "mean_relative_regret": 0.0,
        }

    agreement = sum(
        item.selected_strategy == item.oracle_strategy for item in evaluations
    )
    return {
        "graphs": len(evaluations),
        "oracle_agreement_rate": agreement / len(evaluations),
        "mean_absolute_regret": _mean(item.absolute_regret for item in evaluations),
        "mean_relative_regret": _mean(item.relative_regret for item in evaluations),
    }
