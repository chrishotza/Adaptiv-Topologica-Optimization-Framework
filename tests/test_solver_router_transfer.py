from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.run_solver_router_transfer import (
    _exact_sign_flip_p_one_sided,
    _global_mean_strategy,
    _majority_strategy,
    _summarize,
)


def test_sign_flip_is_bounded() -> None:
    p = _exact_sign_flip_p_one_sided([-1.0, -1.0, -1.0])
    assert 0.0 <= p <= 1.0


def test_training_controls_are_graph_level() -> None:
    training = [
        {"oracle_strategy": "a"},
        {"oracle_strategy": "a"},
        {"oracle_strategy": "b"},
    ]
    assert _majority_strategy(training) == "a"


def test_global_mean_control_uses_training_graph_values() -> None:
    training = [
        {"strategy_metrics": {"a": {"edge_cut": 10.0}, "b": {"edge_cut": 12.0}}},
        {"strategy_metrics": {"a": {"edge_cut": 11.0}, "b": {"edge_cut": 8.0}}},
    ]
    assert _global_mean_strategy(training) == "b"


def test_runtime_and_dominance_are_reported() -> None:
    rows = [
        {
            "router": "nearest",
            "control": "majority",
            "router_relative_regret": 0.0,
            "control_relative_regret": 0.1,
            "router_runtime_ratio": 0.8,
            "control_runtime_ratio": 1.0,
            "router_runtime_dominates_control": True,
        },
        {
            "router": "nearest",
            "control": "majority",
            "router_relative_regret": 0.2,
            "control_relative_regret": 0.1,
            "router_runtime_ratio": 1.1,
            "control_runtime_ratio": 1.0,
            "router_runtime_dominates_control": False,
        },
    ]
    summary = _summarize(rows, "nearest", "majority")
    assert summary["joint_quality_runtime_dominance_rate"] == pytest.approx(0.5)
    assert summary["mean_runtime_delta_router_minus_control"] == pytest.approx(-0.05)


def test_summary_reports_paired_graph_delta() -> None:
    rows = [
        {
            "router": "nearest",
            "control": "majority",
            "router_relative_regret": 0.0,
            "control_relative_regret": 0.1,
            "router_runtime_ratio": 1.0,
            "control_runtime_ratio": 1.0,
            "router_runtime_dominates_control": False,
        },
        {
            "router": "nearest",
            "control": "majority",
            "router_relative_regret": 0.2,
            "control_relative_regret": 0.1,
            "router_runtime_ratio": 1.0,
            "control_runtime_ratio": 1.0,
            "router_runtime_dominates_control": False,
        },
    ]
    summary = _summarize(rows, "nearest", "majority")
    assert summary["graphs"] == 2
    assert summary["mean_delta_router_minus_control"] == pytest.approx(0.0)
    assert summary["router_better_graphs"] == 1
    assert summary["router_worse_graphs"] == 1
