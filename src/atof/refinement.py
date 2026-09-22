from __future__ import annotations

from dataclasses import dataclass


POLICIES = ("fixed", "adaptive")


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

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError("policy must be one of: " + ", ".join(POLICIES))
        if self.period < 1:
            raise ValueError("period must be at least 1")
        if self.patience < 1:
            raise ValueError("patience must be at least 1")

    def after_local_pass(
        self,
        *,
        iteration: int,
        start_cost: float,
        end_cost: float,
        tolerance: float,
    ) -> bool:
        """Observe the local pass and decide whether hybrid refinement fires."""
        gain = start_cost - end_cost
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
        return True

    def record_probe(self, *, iteration: int) -> None:
        """Record a cheap adaptive witness probe."""
        self.probes += 1
        self.last_probe_iteration = iteration

    def record_hybrid_pass(
        self,
        *,
        iteration: int,
        start_cost: float,
        end_cost: float,
    ) -> None:
        """Record the result of a hybrid pass and reset stagnation when useful."""
        self.hybrid_passes += 1
        self.last_hybrid_iteration = iteration
        self.last_hybrid_improved = end_cost < start_cost - 1e-12
        if self.last_hybrid_improved:
            self.stalled_iterations = 0
