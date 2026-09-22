from __future__ import annotations

import random
from collections import defaultdict
from math import sqrt
from typing import Iterable, Mapping, Sequence


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _graph_key(row: Mapping) -> str:
    """Return a collision-safe graph identifier when corpus metadata exists."""
    graph_id = row.get("graph_id")
    if graph_id:
        return str(graph_id)
    return str(row["graph"])


def graph_metric_means(rows: Iterable[Mapping], *, strategy: str, metric: str = "edge_cut") -> dict[str, float]:
    """Aggregate repeated seeds to one metric value per graph instance."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if str(row["strategy"]) != strategy:
            continue
        grouped[_graph_key(row)].append(float(row[metric]))
    if not grouped:
        raise ValueError(f"strategy not found: {strategy}")
    return {graph: _mean(values) for graph, values in sorted(grouped.items())}


def paired_graph_differences(
    rows: Iterable[Mapping],
    *,
    strategy_a: str,
    strategy_b: str,
    metric: str = "edge_cut",
) -> list[float]:
    """Return paired graph-instance differences A - B."""
    by_a = graph_metric_means(rows, strategy=strategy_a, metric=metric)
    by_b = graph_metric_means(rows, strategy=strategy_b, metric=metric)
    graphs = sorted(set(by_a) & set(by_b))
    if not graphs:
        raise ValueError("strategies have no graphs in common")
    return [by_a[graph] - by_b[graph] for graph in graphs]


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    resamples: int = 5000,
    confidence: float = 0.95,
    seed: int = 2024,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the arithmetic mean."""
    if not values:
        raise ValueError("values must not be empty")
    if resamples < 1:
        raise ValueError("resamples must be >= 1")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    rng = random.Random(seed)
    n = len(values)
    samples = [
        _mean([values[rng.randrange(n)] for _ in range(n)])
        for _ in range(resamples)
    ]
    samples.sort()
    alpha = (1.0 - confidence) / 2.0

    def percentile(p: float) -> float:
        position = (len(samples) - 1) * p
        lower = int(position)
        upper = min(lower + 1, len(samples) - 1)
        fraction = position - lower
        return samples[lower] + (samples[upper] - samples[lower]) * fraction

    return percentile(alpha), percentile(1.0 - alpha)


def paired_summary(
    rows: Iterable[Mapping],
    *,
    strategy_a: str,
    strategy_b: str,
    metric: str = "edge_cut",
    resamples: int = 5000,
    seed: int = 2024,
) -> dict:
    """Summarize a paired graph-level comparison with bootstrap uncertainty."""
    materialized = list(rows)
    by_a = graph_metric_means(materialized, strategy=strategy_a, metric=metric)
    by_b = graph_metric_means(materialized, strategy=strategy_b, metric=metric)
    graphs = sorted(set(by_a) & set(by_b))
    if not graphs:
        raise ValueError("strategies have no graphs in common")

    differences = [by_a[graph] - by_b[graph] for graph in graphs]
    lower, upper = bootstrap_mean_ci(differences, resamples=resamples, seed=seed)

    a_wins = sum(by_a[graph] < by_b[graph] for graph in graphs)
    b_wins = sum(by_b[graph] < by_a[graph] for graph in graphs)
    ties = len(graphs) - a_wins - b_wins

    mean_a = _mean([by_a[graph] for graph in graphs])
    mean_b = _mean([by_b[graph] for graph in graphs])
    mean_difference = _mean(differences)
    relative_difference = mean_difference / mean_b if mean_b else 0.0
    std_diff = _sample_std(differences)

    return {
        "strategy_a": strategy_a,
        "strategy_b": strategy_b,
        "metric": metric,
        "graphs": graphs,
        "n_graphs": len(graphs),
        "mean_a": mean_a,
        "mean_b": mean_b,
        "mean_difference_a_minus_b": mean_difference,
        "relative_difference_vs_b": relative_difference,
        "bootstrap_ci": {
            "confidence": 0.95,
            "lower": lower,
            "upper": upper,
            "resamples": resamples,
            "seed": seed,
        },
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "a_win_rate": a_wins / len(graphs),
        "standardized_paired_effect": mean_difference / std_diff if std_diff > 0 else 0.0,
    }
