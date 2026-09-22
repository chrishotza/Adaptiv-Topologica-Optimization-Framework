from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NeighborhoodCreditController:
    threshold: float = 1.15
    max_skips: int = 2
    ema_alpha: float = 0.5
    local_credit: float | None = None
    hybrid_credit: float | None = None
    skips: int = 0
    hybrid_passes: int = 0

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError("threshold must be > 0")
        if self.max_skips < 0:
            raise ValueError("max_skips must be >= 0")
        if not 0 < self.ema_alpha <= 1:
            raise ValueError("ema_alpha must be in (0, 1]")

    def observe_local(self, gain: float, work: int) -> None:
        credit = max(gain, 0.0) / max(work, 1)
        self.local_credit = self._ema(self.local_credit, credit)

    def should_hybrid(self) -> bool:
        if self.hybrid_credit is None or self.local_credit is None:
            return True
        if self.skips >= self.max_skips:
            return True
        return self.hybrid_credit >= self.local_credit * self.threshold

    def record_decision(self, ran_hybrid: bool) -> None:
        if ran_hybrid:
            self.hybrid_passes += 1
            self.skips = 0
        else:
            self.skips += 1

    def observe_hybrid(self, gain: float, work: int) -> None:
        credit = max(gain, 0.0) / max(work, 1)
        self.hybrid_credit = self._ema(self.hybrid_credit, credit)

    def _ema(self, previous: float | None, value: float) -> float:
        if previous is None:
            return value
        return self.ema_alpha * value + (1.0 - self.ema_alpha) * previous
