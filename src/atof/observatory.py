from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TraceSurvival:
    """Descriptive survival/extinction statistics for one optimization trace."""

    iterations: int
    active_iterations: int
    extinction_iteration: int | None
    survival_25: int
    survival_50: int
    survival_75: int
    total_accepted: int

    def to_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "active_iterations": self.active_iterations,
            "extinction_iteration": self.extinction_iteration,
            "survival_25": self.survival_25,
            "survival_50": self.survival_50,
            "survival_75": self.survival_75,
            "total_accepted": self.total_accepted,
        }


@dataclass(frozen=True)
class RegimeComparison:
    """Descriptive group summary; no significance claim is implied."""

    regime: str
    runs: int
    mean_edge_cut: float
    mean_relative_improvement: float
    mean_acceptance_rate: float
    mean_extinction_iteration: float

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "runs": self.runs,
            "mean_edge_cut": self.mean_edge_cut,
            "mean_relative_improvement": self.mean_relative_improvement,
            "mean_acceptance_rate": self.mean_acceptance_rate,
            "mean_extinction_iteration": self.mean_extinction_iteration,
        }


def summarize_survival(trace: Sequence[Mapping]) -> TraceSurvival:
    if not trace:
        raise ValueError("trace must contain at least one row")

    accepted = [int(row["accepted"]) for row in trace]
    iterations = len(accepted)
    total = sum(accepted)
    active = [i + 1 for i, value in enumerate(accepted) if value > 0]
    extinction = active[-1] if active else None

    def survival_at_fraction(fraction: float) -> int:
        threshold = total * fraction
        if threshold <= 0:
            return 0
        cumulative = 0
        for i, value in enumerate(accepted, start=1):
            cumulative += value
            if cumulative >= threshold:
                return i
        return iterations

    return TraceSurvival(
        iterations=iterations,
        active_iterations=len(active),
        extinction_iteration=extinction,
        survival_25=survival_at_fraction(0.25),
        survival_50=survival_at_fraction(0.50),
        survival_75=survival_at_fraction(0.75),
        total_accepted=total,
    )


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def compare_by_regime(rows: Iterable[Mapping]) -> list[RegimeComparison]:
    groups: dict[str, list[Mapping]] = defaultdict(list)
    for row in rows:
        groups[str(row["regime"])].append(row)

    results: list[RegimeComparison] = []
    for regime, group in sorted(groups.items()):
        extinctions = [
            float(row["dynamics"]["extinction_iteration"])
            for row in group
            if row["dynamics"]["extinction_iteration"] is not None
        ]
        results.append(
            RegimeComparison(
                regime=regime,
                runs=len(group),
                mean_edge_cut=_mean(float(row["edge_cut"]) for row in group),
                mean_relative_improvement=_mean(
                    float(row["dynamics"]["relative_improvement"]) for row in group
                ),
                mean_acceptance_rate=_mean(
                    float(row["dynamics"]["acceptance_rate"]) for row in group
                ),
                mean_extinction_iteration=_mean(extinctions),
            )
        )
    return results


def pearson_correlation(rows: Sequence[Mapping], x: str, y: str) -> float:
    """Exploratory Pearson correlation over top-level numeric row fields."""
    pairs = []
    for row in rows:
        xv = row.get(x)
        yv = row.get(y)
        if xv is not None and yv is not None:
            pairs.append((float(xv), float(yv)))

    if len(pairs) < 2:
        return 0.0

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = _mean(xs)
    my = _mean(ys)

    numerator = sum((a - mx) * (b - my) for a, b in pairs)
    dx = sqrt(sum((a - mx) ** 2 for a in xs))
    dy = sqrt(sum((b - my) ** 2 for b in ys))

    if dx == 0 or dy == 0:
        return 0.0
    return numerator / (dx * dy)
