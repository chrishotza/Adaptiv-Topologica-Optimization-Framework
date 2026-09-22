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


def test_early_stop_refinement_tracks_actual_samples_used():
    from atof.strategies import BLOCReloc

    result = BLOCReloc(
        nx.path_graph(16),
        k=2,
        seed=42,
        variant="baseline",
    ).refine(
        iterations=10,
        hybrid_period=5,
        hybrid_samples=20,
        hybrid_policy="early_stop",
        hybrid_batch_samples=5,
        hybrid_idle_patience=2,
    )
    hybrid_rows = [row for row in result.trace if row["hybrid"] == 1]
    assert hybrid_rows
    assert all(0 < row["hybrid_samples"] <= 20 for row in hybrid_rows)
    assert result.hybrid_passes == len(hybrid_rows)