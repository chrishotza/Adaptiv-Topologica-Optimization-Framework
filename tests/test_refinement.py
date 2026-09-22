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
        iteration=2, start_cost=9.0, end_cost=8.0
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


def test_marginal_controller_uses_calibration_then_efficiency():
    controller = RefinementController(
        policy="marginal",
        period=3,
        patience=2,
    )

    assert not controller.after_local_pass(
        iteration=0,
        start_cost=10.0,
        end_cost=9.0,
        tolerance=0.05,
        local_work=10,
    )
    assert not controller.after_local_pass(
        iteration=1,
        start_cost=9.0,
        end_cost=9.0,
        tolerance=0.05,
        local_work=10,
    )
    assert controller.after_local_pass(
        iteration=2,
        start_cost=9.0,
        end_cost=9.0,
        tolerance=0.05,
        local_work=10,
    )

    controller.record_hybrid_pass(
        iteration=2,
        start_cost=9.0,
        end_cost=8.0,
        work=100,
    )
    assert controller.last_hybrid_gain_per_work == pytest.approx(0.01)

    # Local return (0.02/work) is better than hybrid (0.01/work): skip.
    assert not controller.after_local_pass(
        iteration=5,
        start_cost=8.0,
        end_cost=7.8,
        tolerance=0.05,
        local_work=10,
    )

    # After another stalled interval, weak local return should trigger.
    assert not controller.after_local_pass(
        iteration=6,
        start_cost=7.8,
        end_cost=7.8,
        tolerance=0.05,
        local_work=100,
    )
    assert controller.after_local_pass(
        iteration=8,
        start_cost=7.8,
        end_cost=7.8,
        tolerance=0.05,
        local_work=100,
    )


def test_marginal_controller_adapts_next_sample_budget():
    controller = RefinementController(policy="marginal", period=1, patience=1)
    controller.last_local_gain_per_work = 0.005
    controller.last_hybrid_gain_per_work = 0.01

    assert controller.hybrid_sample_budget(100) == 200

    controller.last_hybrid_gain_per_work = 0.0005
    assert controller.hybrid_sample_budget(100) == 25


def test_refinement_controller_accepts_marginal_policy():
    controller = RefinementController(policy="marginal")
    assert controller.policy == "marginal"
