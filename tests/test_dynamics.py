from atof.dynamics import summarize_trace


def test_summarize_trace():
    trace = [
        {"iteration": 0, "weighted_cost": 10.0, "edge_cut": 5, "accepted": 2, "rejected": 3},
        {"iteration": 1, "weighted_cost": 8.0, "edge_cut": 4, "accepted": 1, "rejected": 4},
        {"iteration": 2, "weighted_cost": 8.0, "edge_cut": 4, "accepted": 0, "rejected": 5},
    ]

    summary = summarize_trace(trace)

    assert summary.iterations == 3
    assert summary.initial_weighted_cost == 10.0
    assert summary.final_weighted_cost == 8.0
    assert summary.weighted_improvement == 2.0
    assert summary.relative_improvement == 0.2
    assert summary.total_accepted == 3
    assert summary.total_rejected == 12
    assert summary.active_iterations == 2
    assert summary.extinction_iteration == 2
    assert summary.trailing_inactive_iterations == 1
    assert summary.max_accepted_per_iteration == 2


def test_zero_decisions_have_zero_acceptance_rate():
    trace = [
        {"iteration": 0, "weighted_cost": 3.0, "accepted": 0, "rejected": 0},
    ]
    assert summarize_trace(trace).acceptance_rate == 0.0
