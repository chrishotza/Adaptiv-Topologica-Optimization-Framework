from __future__ import annotations

from experiments.confidence_gate_sensitivity import (
    BUDGET_FACTORS,
    QUANTILES,
)


def test_sensitivity_grid_is_frozen_and_complete() -> None:
    assert BUDGET_FACTORS == (1.0, 1.5, 2.0, 3.0)
    assert QUANTILES == (0.25, 0.50, 0.75)
