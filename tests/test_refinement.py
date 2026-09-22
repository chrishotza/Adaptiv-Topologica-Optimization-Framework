import pytest

from atof.refinement import RefinementController


def test_adaptive_controller_waits_for_stagnation_and_cooldown():
    controller = RefinementController(policy="adaptive", period=3, patience=2)

    assert not controller.after_local_pass(
        iteration=0, start_cost=10.0, end_cost=9.0, tolerance=0.05
    )
    assert not controller.after_local_pass(
        iteration=1, start_cost=9.0, end_cost=9.0, tolerance=0.05
    )
    assert controller.after_local_pass(
        iteration=2, start_cost=9.0, end_cost=9.0, tolerance=0.05
    )

    controller.record_probe(iteration=2, witness=False)
    assert controller.probes == 1
    controller.record_hybrid_pass(
        iteration=2, start_cost=9.0, end_cost=8.0, samples_used=10
    )
    assert controller.hybrid_passes == 1
    assert controller.last_hybrid_improved is True
    assert controller.stalled_iterations == 0

    assert not controller.after_local_pass(
        iteration=3, start_cost=8.0, end_cost=8.0, tolerance=0.05
    )
    assert not controller.after_local_pass(
        iteration=4, start_cost=8.0, end_cost=8.0, tolerance=0.05
    )
    assert controller.after_local_pass(
        iteration=5, start_cost=8.0, end_cost=8.0, tolerance=0.05
    )


def test_fixed_controller_preserves_periodic_schedule():
    controller = RefinementController(policy="fixed", period=3, patience=9)

    assert not controller.after_local_pass(
        iteration=0, start_cost=10.0, end_cost=10.0, tolerance=0.05
    )
    assert not controller.after_local_pass(
        iteration=1, start_cost=10.0, end_cost=9.0, tolerance=0.05
    )
    assert controller.after_local_pass(
        iteration=2, start_cost=9.0, end_cost=8.0, tolerance=0.05
    )





def test_controller_enforces_cooldown_after_hybrid_pass():
    controller = RefinementController(policy="adaptive", period=3, patience=1)
    controller.record_hybrid_pass(
        iteration=2, start_cost=10.0, end_cost=9.0
    )

    assert not controller.after_local_pass(
        iteration=3, start_cost=9.0, end_cost=9.0, tolerance=0.05
    )
    assert not controller.after_local_pass(
        iteration=4, start_cost=9.0, end_cost=9.0, tolerance=0.05
    )
    assert controller.after_local_pass(
        iteration=5, start_cost=9.0, end_cost=9.0, tolerance=0.05
    )


def test_budgeted_controller_adjusts_sample_budget_by_marginal_return():
    controller = RefinementController(policy="budgeted", sample_budget=100, min_samples=25, max_samples=200)
    assert controller.sample_budget == 100
    controller.record_hybrid_pass(
        iteration=4, start_cost=10.0, end_cost=8.0, samples_used=100
    )
    assert controller.sample_budget == 125
    controller.record_hybrid_pass(
        iteration=9, start_cost=8.0, end_cost=8.0, samples_used=125
    )
    assert controller.sample_budget == 62
    assert controller.budget_adjustments == 2

@pytest.mark.parametrize(
    "kwargs",
    [
        {"policy": "unknown"},
        {"period": 0},
        {"patience": 0},
    ],
)
def test_refinement_controller_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        RefinementController(**kwargs)
