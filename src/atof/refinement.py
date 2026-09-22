from __future__ import annotations

from dataclasses import dataclass


POLICIES = ("fixed", "adaptive", "marginal")


@dataclass
class RefinementController:
    """State-aware controller for optional expensive local refinement.

    ``fixed`` reproduces the existing periodic schedule. ``adaptive`` waits
    for a stagnation signal before paying for two-node swap refinement, while
    respecting ``period`` as a minimum cooldown between expensive passes.
    """

    policy: str = "fixed"
    period: int = 5
    patience: int = 2
    stalled_iterations: int = 0
    last_hybrid_iteration: int | None = None
    last_probe_iteration: int | None = None
    hybrid_passes: int = 0
    probes: int = 0
    last_hybrid_improved: bool | None = None
    witness_patience: int = 2
    witness_misses: int = 0
    last_local_gain_per_work: float | None = None
    last_hybrid_gain_per_work: float | None = None
    last_hybrid_work: int = 0

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("policy must be one of: " + ", ".join(POLICIES))
        if self.period < 1:
            raise ValueError("period must be at least 1")
        if self.patience < 1:
            raise ValueError("patience must be at least 1")
        if self.witness_patience < 1:
            raise ValueError("witness_patience must be at least 1")

    def after_local_pass(
        self,
        *,
        iteration: int,
        start_cost: float,
        end_cost: float,
        tolerance: float,
        local_work: int = 0,
    ) -> bool:
        """Observe the local pass and decide whether hybrid refinement fires."""
        gain = start_cost - end_cost
        self.last_local_gain_per_work = (
            gain / local_work if local_work > 0 else 0.0
        )
        threshold = max(tolerance, 1e-12)
        if gain <= threshold:
            self.stalled_iterations += 1
        else:
            self.stalled_iterations = 0

        if self.policy == "fixed":
            return (iteration + 1) % self.period == 0

        if iteration + 1 < self.period:
            return False
        if self.stalled_iterations < self.patience:
            return False
        if (
            self.last_hybrid_iteration is not None
            and iteration - self.last_hybrid_iteration < self.period
        ):
            return False
        if (
            self.last_probe_iteration is not None
            and iteration - self.last_probe_iteration < self.period
        ):
            return False
        if self.policy == "marginal":
            if self.last_hybrid_gain_per_work is None:
                return True
            local_eff = self.last_local_gain_per_work or 0.0
            return local_eff <= self.last_hybrid_gain_per_work
        return True

    def record_probe(self, *, iteration: int, witness: bool) -> None:
        """Record a cheap adaptive witness probe and its evidence."""
        self.probes += 1
        self.last_probe_iteration = iteration
        if witness:
            self.witness_misses = 0
        else:
            self.witness_misses += 1

    def record_hybrid_pass(
        self,
        *,
        iteration: int,
        start_cost: float,
        end_cost: float,
        work: int = 0,
    ) -> None:
        """Record the result of a hybrid pass and reset stagnation when useful."""
        self.hybrid_passes += 1
        self.last_hybrid_iteration = iteration
        self.last_hybrid_improved = end_cost < start_cost - 1e-12
        self.last_hybrid_work = work
        gain = start_cost - end_cost
        self.last_hybrid_gain_per_work = (
            gain / work if work > 0 else 0.0
        )
        if self.last_hybrid_improved:
            self.stalled_iterations = 0

    def hybrid_sample_budget(
        self,
        base_samples: int,
        *,
        min_fraction: float = 0.25,
        max_multiple: float = 2.0,
    ) -> int:
        """Adapt the next expensive-pass budget from observed marginal return."""
        if base_samples <= 0:
            return 0
        if self.policy != "marginal":
            return base_samples
        if self.last_hybrid_gain_per_work is None:
            return base_samples
        local_eff = self.last_local_gain_per_work or 0.0
        hybrid_eff = self.last_hybrid_gain_per_work
        if local_eff <= 0.0:
            factor = max_multiple if hybrid_eff > 0.0 else min_fraction
        else:
            factor = hybrid_eff / local_eff
            factor = max(min_fraction, min(max_multiple, factor))
        return max(1, int(round(base_samples * factor)))
