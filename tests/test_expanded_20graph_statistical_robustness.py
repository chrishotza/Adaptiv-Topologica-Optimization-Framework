from __future__ import annotations

from experiments.run_expanded_20graph_statistical_robustness import (
    bootstrap_mean_ci,
    exact_sign_test,
)


def test_exact_sign_test_handles_ties_and_is_bounded():
    assert exact_sign_test([0.0, 0.0, 0.0]) == 1.0
    assert 0.0 <= exact_sign_test([-1.0, 1.0]) <= 1.0
    assert exact_sign_test([-1.0, -1.0]) == 1.0


def test_bootstrap_is_deterministic_for_seed():
    values = [-0.4, -0.1, 0.0, 0.2]
    first = bootstrap_mean_ci(values, resamples=2000, seed=2024)
    second = bootstrap_mean_ci(values, resamples=2000, seed=2024)
    assert first == second
    assert first[0] <= first[1]
