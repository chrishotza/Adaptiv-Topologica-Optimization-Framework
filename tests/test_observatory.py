from atof.observatory import (
    compare_by_regime,
    pearson_correlation,
    summarize_survival,
    survival_curve,
)


def _trace(values):
    return [
        {
            "iteration": i,
            "weighted_cost": 10.0 - i,
            "accepted": accepted,
            "rejected": 2,
            "edge_cut": 5,
        }
        for i, accepted in enumerate(values)
    ]


def test_summarize_survival():
    summary = summarize_survival(_trace([2, 1, 0, 0]))
    assert summary.iterations == 4
    assert summary.active_iterations == 2
    assert summary.activity_fraction == 0.5
    assert summary.extinction_iteration == 2
    assert summary.total_accepted == 3
    assert summary.time_to_25_activity == 1
    assert summary.time_to_50_activity == 1
    assert summary.time_to_75_activity == 2


def test_survival_curve_is_descriptive():
    curve = survival_curve([_trace([1, 1, 0]), _trace([1, 0, 0])])
    assert curve == [1.0, 0.5, 0.0]


def test_regime_comparison_and_correlation():
    rows = [
        {
            "regime": "hub_dominated",
            "edge_cut": 10,
            "dynamics": {
                "relative_improvement": 0.2,
                "acceptance_rate": 0.5,
                "extinction_iteration": 4,
            },
        },
        {
            "regime": "hub_dominated",
            "edge_cut": 8,
            "dynamics": {
                "relative_improvement": 0.4,
                "acceptance_rate": 0.25,
                "extinction_iteration": 6,
            },
        },
    ]

    result = compare_by_regime(rows)
    assert len(result) == 1
    assert result[0].runs == 2
    assert result[0].mean_edge_cut == 9.0
    assert result[0].mean_extinction_iteration == 5.0

    assert round(
        pearson_correlation(
            [{"x": 1, "y": 2}, {"x": 2, "y": 4}, {"x": 3, "y": 6}],
            "x",
            "y",
        ),
        6,
    ) == 1.0
