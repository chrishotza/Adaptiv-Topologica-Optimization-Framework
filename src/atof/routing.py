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

SCALERS = ("minmax", "std", "iqr")
METRICS = ("l2", "l1")


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
    "without_degree_hub_mesoscopic": tuple(
        feature
        for feature in FEATURES
        if feature not in FEATURE_GROUPS["degree_hub"]
        and feature not in FEATURE_GROUPS["mesoscopic"]
    ),
    "without_degree_hub_global_paths": tuple(
        feature
        for feature in FEATURES
        if feature not in FEATURE_GROUPS["degree_hub"]
        and feature not in FEATURE_GROUPS["global_paths"]
    ),
    "without_mesoscopic_global_paths": tuple(
        feature
        for feature in FEATURES
        if feature not in FEATURE_GROUPS["mesoscopic"]
        and feature not in FEATURE_GROUPS["global_paths"]
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


def _distance(
    a: Sequence[float],
    b: Sequence[float],
    scale: Sequence[float],
    metric: str = "l2",
) -> float:
    deltas = [
        abs((x - y) / s)
        for x, y, s in zip(a, b, scale)
        if s > 0
    ]
    if metric == "l1":
        return sum(deltas)
    if metric == "l2":
        return sqrt(sum(delta * delta for delta in deltas))
    raise ValueError("metric must be 'l1' or 'l2'")


def _feature_scales(
    vectors: Sequence[Sequence[float]],
    mode: str,
) -> tuple[float, ...]:
    if mode not in SCALERS:
        raise ValueError("scale mode must be one of: " + ", ".join(SCALERS))
    width = len(vectors[0])
    scales: list[float] = []
    for i in range(width):
        values = sorted(float(vector[i]) for vector in vectors)
        if mode == "minmax":
            scale = values[-1] - values[0]
        elif mode == "std":
            mean = sum(values) / len(values)
            scale = sqrt(
                sum((value - mean) ** 2 for value in values) / len(values)
            )
        else:
            if len(values) == 1:
                scale = 0.0
            else:
                q1_index = 0.25 * (len(values) - 1)
                q3_index = 0.75 * (len(values) - 1)
                lo0, lo1 = int(q1_index), min(int(q1_index) + 1, len(values) - 1)
                hi0, hi1 = int(q3_index), min(int(q3_index) + 1, len(values) - 1)
                q1 = values[lo0] + (values[lo1] - values[lo0]) * (q1_index - lo0)
                q3 = values[hi0] + (values[hi1] - values[hi0]) * (q3_index - hi0)
                scale = q3 - q1
        scales.append(scale if scale > 0 else 1.0)
    return tuple(scales)


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

    def __init__(
        self,
        features: Sequence[str] | None = None,
        scale_mode: str = "minmax",
        metric: str = "l2",
    ) -> None:
        self.features = resolve_features(features)
        self.scale_mode = scale_mode
        self.metric = metric
        if scale_mode not in SCALERS:
            raise ValueError("scale mode must be one of: " + ", ".join(SCALERS))
        if metric not in METRICS:
            raise ValueError("metric must be one of: " + ", ".join(METRICS))
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

        scale = _feature_scales(vectors, self.scale_mode)

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

    def rank(self, topology: Mapping) -> tuple[str, ...]:
        """Rank candidate strategies by topology-centroid distance."""
        if not self._centroids:
            raise RuntimeError("router must be fitted before rank()")

        vector = topology_vector(topology, self.features)
        return tuple(
            sorted(
                self._centroids,
                key=lambda strategy: (
                    _distance(
                        vector,
                        self._centroids[strategy],
                        self._scale,
                        self.metric,
                    ),
                    strategy,
                ),
            )
        )

    def predict(self, topology: Mapping) -> str:
        return self.rank(topology)[0]


class NearestTopologyRouter:
    """1-nearest-neighbor router in standardized topology-feature space."""

    def __init__(
        self,
        features: Sequence[str] | None = None,
        scale_mode: str = "minmax",
        metric: str = "l2",
    ) -> None:
        self.features = resolve_features(features)
        self.scale_mode = scale_mode
        self.metric = metric
        if scale_mode not in SCALERS:
            raise ValueError("scale mode must be one of: " + ", ".join(SCALERS))
        if metric not in METRICS:
            raise ValueError("metric must be one of: " + ", ".join(METRICS))
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
        scale = _feature_scales(vectors, self.scale_mode)

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

    def rank(self, topology: Mapping) -> tuple[str, ...]:
        """Rank candidate strategies by nearest observed topology examples."""
        if not self._training:
            raise RuntimeError("router must be fitted before rank()")

        vector = topology_vector(topology, self.features)
        ranked: list[str] = []
        for _, strategy, _ in sorted(
            self._training,
            key=lambda item: (
                _distance(
                    vector,
                    item[2],
                    self._scale,
                    self.metric,
                ),
                item[1],
                item[0],
            ),
        ):
            if strategy not in ranked:
                ranked.append(strategy)
        return tuple(ranked)

    def predict(self, topology: Mapping) -> str:
        return self.rank(topology)[0]


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
