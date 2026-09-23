from __future__ import annotations

from experiments.trajectory_aware_allocation import (
    _run_policy,
    _runtime_per_edge,
)


def _row() -> dict:
    return {
        "graph_id": "g",
        "corpus": "test",
        "edges": 100,
        "topology": {
            "density": 0.1,
            "avg_degree": 2.0,
            "degree_std": 0.2,
            "hub_ratio": 1.1,
            "degree_gini": 0.1,
            "clustering": 0.2,
            "transitivity": 0.2,
            "core_number": 2.0,
            "diameter": 5.0,
            "avg_path_length": 2.0,
            "modularity": 0.2,
        },
        "oracle_strategy": "solver_b",
        "strategy_metrics": {
            "solver_a": {"edge_cut": 120.0, "runtime_seconds": 0.10},
            "solver_b": {"edge_cut": 100.0, "runtime_seconds": 0.20},
            "solver_c": {"edge_cut": 90.0, "runtime_seconds": 0.20},
        },
    }


def test_runtime_model_uses_training_only_values() -> None:
    training = [
        {
            "edges": 100,
            "strategy_metrics": {
                "solver_a": {"runtime_seconds": 1.0},
                "solver_b": {"runtime_seconds": 2.0},
            },
        },
        {
            "edges": 200,
            "strategy_metrics": {
                "solver_a": {"runtime_seconds": 1.0},
                "solver_b": {"runtime_seconds": 4.0},
            },
        },
    ]

    costs = _runtime_per_edge(training)

    assert costs["solver_a"] == 0.005
    assert costs["solver_b"] == 0.02


def test_budget_one_x_allows_only_first_ranked_action() -> None:
    row = _row()
    result = _run_policy(
        row,
        ("solver_a", "solver_b", "solver_c"),
        {"solver_a": 1.0, "solver_b": 1.0, "solver_c": 1.0},
        budget_factor=1.0,
        min_relative_improvement=0.01,
    )

    assert result["chosen_strategies"] == ["solver_a"]
    assert result["selected_strategy"] == "solver_a"
    assert result["actions"] == 1
    assert result["stop_reason"] == "budget_exhausted"


def test_sequential_policy_keeps_a_materially_better_second_action() -> None:
    row = _row()
    result = _run_policy(
        row,
        ("solver_a", "solver_b", "solver_c"),
        {"solver_a": 1.0, "solver_b": 1.0, "solver_c": 1.0},
        budget_factor=2.0,
        min_relative_improvement=0.01,
    )

    assert result["chosen_strategies"] == ["solver_a", "solver_b"]
    assert result["selected_strategy"] == "solver_b"
    assert result["actions"] == 2
