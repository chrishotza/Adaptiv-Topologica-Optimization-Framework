from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isfinite, log1p
from typing import Mapping, Sequence

import networkx as nx

from .topology import TopologyProfile, TopologyProfiler


def _finite(value: float, default: float = 0.0) -> float:
    value = float(value)
    return value if isfinite(value) else default


@dataclass(frozen=True)
class RegimeSignatureV2:
    """Descriptive graph signature for topology-aware routing research.

    Measurements are separated from policy. The flags below are transparent
    heuristics and are not presented as validated universal classifiers.
    """

    node_count: int
    edge_count: int
    k: int
    density: float
    avg_degree: float
    degree_std: float
    degree_cv: float
    max_degree: int
    hub_ratio: float
    hub_concentration: float
    degree_gini: float
    clustering: float
    transitivity: float
    assortativity: float
    core_number: float
    diameter: float
    avg_path_length: float
    communities: int
    modularity: float
    component_count: int
    giant_component_fraction: float
    edge_to_node: float
    log_nodes: float
    log_edges: float
    hub_dominated: bool
    modular: bool
    regular_like: bool
    disconnected: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def regime_flags(self) -> tuple[str, ...]:
        flags: list[str] = []
        if self.disconnected:
            flags.append("disconnected")
        if self.hub_dominated:
            flags.append("hub_dominated")
        if self.modular:
            flags.append("modular")
        if self.regular_like:
            flags.append("regular_like")
        if not flags:
            flags.append("mixed")
        return tuple(flags)


def build_regime_signature_v2(
    graph: nx.Graph,
    *,
    k: int = 2,
    profile: TopologyProfile | None = None,
    hub_ratio_threshold: float = 3.0,
    degree_gini_threshold: float = 0.45,
    hub_concentration_threshold: float = 0.10,
    modularity_threshold: float = 0.30,
    degree_cv_threshold: float = 0.20,
) -> RegimeSignatureV2:
    """Build an interpretable topology signature without fitting on labels."""
    if graph.number_of_nodes() == 0:
        raise ValueError("cannot profile an empty graph")
    if k < 2:
        raise ValueError("k must be at least 2")

    profile = profile or TopologyProfiler().profile(graph)
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    total_degree = 2.0 * m
    components = list(nx.connected_components(graph))
    giant = max((len(component) for component in components), default=0)
    giant_fraction = giant / n if n else 0.0
    degree_cv = profile.degree_std / profile.avg_degree if profile.avg_degree else 0.0
    hub_concentration = profile.max_degree / total_degree if total_degree else 0.0
    modularity = _finite(profile.modularity)
    assortativity = _finite(profile.assortativity)

    return RegimeSignatureV2(
        node_count=n,
        edge_count=m,
        k=k,
        density=_finite(profile.density),
        avg_degree=_finite(profile.avg_degree),
        degree_std=_finite(profile.degree_std),
        degree_cv=_finite(degree_cv),
        max_degree=int(profile.max_degree),
        hub_ratio=_finite(profile.hub_ratio),
        hub_concentration=_finite(hub_concentration),
        degree_gini=_finite(profile.degree_gini),
        clustering=_finite(profile.clustering),
        transitivity=_finite(profile.transitivity),
        assortativity=assortativity,
        core_number=_finite(profile.core_number),
        diameter=_finite(profile.diameter),
        avg_path_length=_finite(profile.avg_path_length),
        communities=int(profile.communities),
        modularity=modularity,
        component_count=len(components),
        giant_component_fraction=_finite(giant_fraction),
        edge_to_node=(m / n) if n else 0.0,
        log_nodes=log1p(n),
        log_edges=log1p(m),
        hub_dominated=(
            profile.hub_ratio >= hub_ratio_threshold
            or profile.degree_gini >= degree_gini_threshold
            or hub_concentration >= hub_concentration_threshold
        ),
        modular=modularity >= modularity_threshold,
        regular_like=degree_cv <= degree_cv_threshold,
        disconnected=len(components) > 1,
    )


@dataclass(frozen=True)
class TrajectoryState:
    """Online search-state signal extracted from an optimization trace."""

    state: str
    iteration: int
    cost: float
    stagnation_length: int
    trailing_inactive_iterations: int
    acceptance_rate: float
    recent_gain: float
    gain_decay: float | None
    recent_accepted: int
    recent_rejected: int
    boundary_pressure: float | None = None
    hub_exposure: float | None = None
    block_gain_variance: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TrajectoryMonitor:
    """State monitor using only observations available up to the current step.

    No future trace values or oracle labels are used. Thresholds are explicit
    so they can be frozen before a confirmatory benchmark.
    """

    window: int = 3
    stagnation_patience: int = 3
    extinction_patience: int = 4
    exploration_acceptance_rate: float = 0.35
    exploration_gain_floor: float = 1e-3
    premature_window: int = 3
    premature_min_accepts: int = 1
    tolerance: float = 1e-12

    def __post_init__(self) -> None:
        if self.window < 1:
            raise ValueError("window must be at least 1")
        if self.stagnation_patience < 1:
            raise ValueError("stagnation_patience must be at least 1")
        if self.extinction_patience < 1:
            raise ValueError("extinction_patience must be at least 1")
        if self.premature_window < 1:
            raise ValueError("premature_window must be at least 1")
        if self.premature_min_accepts < 0:
            raise ValueError("premature_min_accepts must be non-negative")
        if not 0.0 <= self.exploration_acceptance_rate <= 1.0:
            raise ValueError("exploration_acceptance_rate must be in [0,1]")
        if self.exploration_gain_floor < 0.0:
            raise ValueError("exploration_gain_floor must be non-negative")

    def observe(self, trace: Sequence[Mapping[str, float | int]]) -> TrajectoryState:
        """Return the state supported by the supplied trace prefix."""
        if not trace:
            raise ValueError("trace must contain at least one observation")

        required = {"weighted_cost", "accepted", "rejected"}
        missing = required.difference(trace[0])
        if missing:
            raise ValueError(f"trace is missing required fields: {sorted(missing)}")

        rows = list(trace)
        costs = [float(row["weighted_cost"]) for row in rows]
        accepted = [int(row["accepted"]) for row in rows]
        rejected = [int(row["rejected"]) for row in rows]

        current_cost = costs[-1]
        changes = [costs[i - 1] - costs[i] for i in range(1, len(costs))]
        recent_changes = changes[-self.window:]
        recent_gain = sum(recent_changes)
        recent_accepted = sum(accepted[-self.window:])
        recent_rejected = sum(rejected[-self.window:])
        decisions = recent_accepted + recent_rejected
        acceptance_rate = recent_accepted / decisions if decisions else 0.0

        stagnation = 0
        for gain in reversed(changes):
            if gain <= self.tolerance:
                stagnation += 1
            else:
                break

        trailing_inactive = 0
        for count in reversed(accepted):
            if count == 0:
                trailing_inactive += 1
            else:
                break

        gain_decay: float | None = None
        if len(changes) >= 2 * self.window:
            previous = sum(changes[-2 * self.window : -self.window])
            if previous > self.tolerance:
                ratio = max(0.0, min(recent_gain / previous, 1.0))
                gain_decay = 1.0 - ratio

        early = accepted[: self.premature_window]
        premature = (
            len(rows) >= self.premature_window
            and sum(early) < self.premature_min_accepts
        )
        exploratory_excess = (
            recent_accepted > 0
            and acceptance_rate >= self.exploration_acceptance_rate
            and recent_gain <= self.exploration_gain_floor
        )
        extinct = trailing_inactive >= self.extinction_patience
        stagnating = stagnation >= self.stagnation_patience

        if premature:
            state = "premature_collapse"
        elif extinct:
            state = "extinct"
        elif exploratory_excess:
            state = "exploratory_excess"
        elif stagnating:
            state = "stagnating"
        else:
            state = "active"

        return TrajectoryState(
            state=state,
            iteration=len(rows) - 1,
            cost=current_cost,
            stagnation_length=stagnation,
            trailing_inactive_iterations=trailing_inactive,
            acceptance_rate=acceptance_rate,
            recent_gain=recent_gain,
            gain_decay=gain_decay,
            recent_accepted=recent_accepted,
            recent_rejected=recent_rejected,
            boundary_pressure=_optional_metric(rows[-1], "boundary_pressure"),
            hub_exposure=_optional_metric(rows[-1], "hub_exposure"),
            block_gain_variance=_optional_metric(rows[-1], "block_gain_variance"),
        )


def _optional_metric(row: Mapping[str, float | int], name: str) -> float | None:
    if name not in row:
        return None
    try:
        value = float(row[name])
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


@dataclass(frozen=True)
class ControllerDecision:
    action: str
    target_strategy: str | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioControllerV2:
    """Budget-aware continue/intensify/switch/stop policy.

    probe_scores contains only observed scores from bounded probes.
    No graph-level oracle labels are accessed.
    """

    switch_min_relative_gain: float = 0.01
    stop_budget_fraction: float = 0.05
    switch_budget_fraction: float = 0.15

    def decide(
        self,
        *,
        trajectory: TrajectoryState,
        current_strategy: str,
        current_cost: float,
        probe_scores: Mapping[str, float] | None = None,
        remaining_budget_fraction: float = 1.0,
    ) -> ControllerDecision:
        if remaining_budget_fraction < 0.0:
            raise ValueError("remaining_budget_fraction must be non-negative")
        if current_cost < 0.0:
            raise ValueError("current_cost must be non-negative")

        probes = {
            str(strategy): float(score)
            for strategy, score in (probe_scores or {}).items()
            if float(score) >= 0.0
        }
        better = {
            strategy: score
            for strategy, score in probes.items()
            if strategy != current_strategy
            and score <= current_cost * (1.0 - self.switch_min_relative_gain)
        }

        if better and remaining_budget_fraction >= self.switch_budget_fraction:
            target = min(better, key=lambda item: (better[item], item))
            return ControllerDecision(
                action="switch",
                target_strategy=target,
                reason="bounded probe observed a materially lower cost",
            )

        if trajectory.state == "active":
            return ControllerDecision(
                action="continue",
                target_strategy=current_strategy,
                reason="recent prefix still shows productive progress",
            )

        if trajectory.state == "premature_collapse":
            if probes and remaining_budget_fraction >= self.switch_budget_fraction:
                target = min(probes, key=lambda item: (probes[item], item))
                if target != current_strategy:
                    return ControllerDecision(
                        action="switch",
                        target_strategy=target,
                        reason="early collapse signal plus an available alternate probe",
                    )
            if remaining_budget_fraction > self.stop_budget_fraction:
                return ControllerDecision(
                    action="intensify",
                    target_strategy=current_strategy,
                    reason="early collapse signal without a sufficiently strong switch witness",
                )

        if trajectory.state == "stagnating":
            if remaining_budget_fraction > self.stop_budget_fraction:
                return ControllerDecision(
                    action="intensify",
                    target_strategy=current_strategy,
                    reason="stagnation threshold reached and budget remains",
                )

        if trajectory.state == "exploratory_excess":
            if better:
                target = min(better, key=lambda item: (better[item], item))
                return ControllerDecision(
                    action="switch",
                    target_strategy=target,
                    reason="high acceptance with weak gain and a better bounded probe",
                )
            return ControllerDecision(
                action="stop",
                target_strategy=current_strategy,
                reason="high search activity is not producing sufficient gain",
            )

        if trajectory.state == "extinct":
            return ControllerDecision(
                action="stop",
                target_strategy=current_strategy,
                reason="accepted moves have been absent for the configured extinction window",
            )

        if remaining_budget_fraction <= self.stop_budget_fraction:
            return ControllerDecision(
                action="stop",
                target_strategy=current_strategy,
                reason="remaining budget is below the stop threshold",
            )

        return ControllerDecision(
            action="continue",
            target_strategy=current_strategy,
            reason="no stronger transition signal is available",
        )


def adaptive_regime_summary(
    graph: nx.Graph,
    *,
    k: int = 2,
    profile: TopologyProfile | None = None,
) -> dict[str, object]:
    """Convenience payload for provenance and AI-facing observability."""
    signature = build_regime_signature_v2(graph, k=k, profile=profile)
    return {
        "schema": "atof.regime.v2",
        "signature": signature.to_dict(),
        "regime_flags": list(signature.regime_flags),
    }
