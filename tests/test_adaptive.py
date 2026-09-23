import networkx as nx

from atof.adaptive import (
    PortfolioControllerV2,
    TrajectoryMonitor,
    build_regime_signature_v2,
)


def test_regime_signature_v2_is_descriptive_and_finite():
    graph = nx.star_graph(5)
    signature = build_regime_signature_v2(graph, k=2)

    assert signature.node_count == 6
    assert signature.edge_count == 5
    assert signature.hub_dominated
    assert signature.hub_concentration > 0.0
    assert all(value == value for value in signature.to_dict().values() if isinstance(value, float))


def test_trajectory_monitor_detects_stagnation_from_prefix_only():
    trace = [
        {"weighted_cost": 10.0, "accepted": 2, "rejected": 2},
        {"weighted_cost": 9.0, "accepted": 1, "rejected": 3},
        {"weighted_cost": 9.0, "accepted": 1, "rejected": 3},
        {"weighted_cost": 9.0, "accepted": 0, "rejected": 4},
        {"weighted_cost": 9.0, "accepted": 0, "rejected": 4},
    ]

    state = TrajectoryMonitor(
        stagnation_patience=2,
        extinction_patience=10,
        premature_window=2,
    ).observe(trace)

    assert state.state == "stagnating"
    assert state.stagnation_length == 3
    assert state.recent_gain == 0.0


def test_controller_switches_only_on_observed_probe_gain():
    trace = [
        {"weighted_cost": 10.0, "accepted": 1, "rejected": 2},
        {"weighted_cost": 9.0, "accepted": 1, "rejected": 2},
        {"weighted_cost": 9.0, "accepted": 0, "rejected": 3},
        {"weighted_cost": 9.0, "accepted": 0, "rejected": 3},
    ]
    state = TrajectoryMonitor(stagnation_patience=2).observe(trace)

    decision = PortfolioControllerV2().decide(
        trajectory=state,
        current_strategy="baseline",
        current_cost=9.0,
        probe_scores={"alternative": 8.7},
        remaining_budget_fraction=0.5,
    )

    assert decision.action == "switch"
    assert decision.target_strategy == "alternative"
