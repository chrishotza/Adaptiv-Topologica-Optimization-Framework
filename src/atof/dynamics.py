from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class DynamicsSummary:
    """Descriptive summary of an optimization trace.

    The terminology is deliberately operational: an "active iteration" is
    one with at least one accepted move. No causal interpretation is implied.
    """

    iterations: int
    initial_weighted_cost: float
    final_weighted_cost: float
    weighted_improvement: float
    relative_improvement: float
    total_accepted: int
    total_rejected: int
    acceptance_rate: float
    active_iterations: int
    extinction_iteration: int | None
    trailing_inactive_iterations: int
    max_accepted_per_iteration: int

    def to_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "initial_weighted_cost": self.initial_weighted_cost,
            "final_weighted_cost": self.final_weighted_cost,
            "weighted_improvement": self.weighted_improvement,
            "relative_improvement": self.relative_improvement,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "acceptance_rate": self.acceptance_rate,
            "active_iterations": self.active_iterations,
            "extinction_iteration": self.extinction_iteration,
            "trailing_inactive_iterations": self.trailing_inactive_iterations,
            "max_accepted_per_iteration": self.max_accepted_per_iteration,
        }


def summarize_trace(trace: Sequence[Mapping]) -> DynamicsSummary:
    """Summarize a BLOC-style trace without requiring the optimizer itself."""
    if not trace:
        raise ValueError("trace must contain at least one iteration")

    required = {"weighted_cost", "accepted", "rejected"}
    missing = required.difference(trace[0])
    if missing:
        raise ValueError(f"trace is missing required fields: {sorted(missing)}")

    costs = [float(row["weighted_cost"]) for row in trace]
    accepted = [int(row["accepted"]) for row in trace]
    rejected = [int(row["rejected"]) for row in trace]

    initial = costs[0]
    final = costs[-1]
    improvement = initial - final
    relative = improvement / initial if initial else 0.0

    total_accepted = sum(accepted)
    total_rejected = sum(rejected)
    decisions = total_accepted + total_rejected
    acceptance_rate = total_accepted / decisions if decisions else 0.0

    active = [i for i, count in enumerate(accepted) if count > 0]
    extinction = active[-1] + 1 if active else None

    trailing = 0
    for count in reversed(accepted):
        if count != 0:
            break
        trailing += 1

    return DynamicsSummary(
        iterations=len(trace),
        initial_weighted_cost=initial,
        final_weighted_cost=final,
        weighted_improvement=improvement,
        relative_improvement=relative,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        acceptance_rate=acceptance_rate,
        active_iterations=len(active),
        extinction_iteration=extinction,
        trailing_inactive_iterations=trailing,
        max_accepted_per_iteration=max(accepted),
    )


def summarize_many(traces: Iterable[Sequence[Mapping]]) -> list[DynamicsSummary]:
    return [summarize_trace(trace) for trace in traces]
