from __future__ import annotations

import pytest

from experiments.run_kway_state_of_art_benchmark import (
    K_VALUES,
    STRATEGIES,
    _aggregate,
    _summarize_graph,
)


def test_kway_surface_matches_locked_protocol() -> None:
    assert K_VALUES == (4, 8, 32, 64)
    assert len(STRATEGIES) == 8
    assert "metis" in STRATEGIES
    assert "kahip" in STRATEGIES
    assert "kaminpar_default" in STRATEGIES
    assert "kaminpar_strong" in STRATEGIES


def test_unmatched_graphs_do_not_enter_aggregate() -> None:
    rows = [
        {
            "strategy": "a",
            "status": "ok",
            "edge_cut": 10,
            "balance_error": 0.0,
            "runtime_seconds": 2.0,
        },
        {
            "strategy": "b",
            "status": "ok",
            "edge_cut": 10,
            "balance_error": 0.0,
            "runtime_seconds": 1.0,
        },
        {
            "strategy": "c",
            "status": "error",
            "error": "backend unavailable",
        },
    ]
    summary = _summarize_graph(rows, ("a", "b", "c"))
    assert summary["matched"] is False
    assert _aggregate({"g": summary}, ("a", "b", "c"))["matched_graphs"] == 0


def test_matched_graph_is_aggregated() -> None:
    rows = [
        {"strategy": "a", "status": "ok", "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 2.0},
        {"strategy": "b", "status": "ok", "edge_cut": 12, "balance_error": 0.0, "runtime_seconds": 1.0},
    ]
    summary = _summarize_graph(rows, ("a", "b"))
    assert summary["matched"] is True
    assert summary["best_quality"] == "a"
    aggregate = _aggregate({"g": summary}, ("a", "b"))
    assert aggregate["matched_graphs"] == 1
    assert aggregate["strategies"]["a"]["mean_relative_quality_gap"] == pytest.approx(0.0)
    assert aggregate["strategies"]["b"]["mean_relative_quality_gap"] == pytest.approx(0.2)