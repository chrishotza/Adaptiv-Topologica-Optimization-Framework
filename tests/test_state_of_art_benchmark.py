from __future__ import annotations

import pytest

from experiments.run_state_of_art_benchmark import (
    CORE_STRATEGIES,
    _aggregate_graph_summaries,
    _summarize_graph,
)


def test_core_strategy_surface_is_locked() -> None:
    assert CORE_STRATEGIES == (
        "bloc_reloc_baseline",
        "bloc_reloc_affinity",
        "bloc_reloc_hybrid_fixed",
        "bloc_reloc_adaptive",
        "kernighan_lin",
        "metis",
        "kahip",
        "kaminpar_default",
        "kaminpar_strong",
        "mtkahypar_default",
        "mtkahypar_quality",
    )


def test_graph_summary_normalizes_quality_and_runtime() -> None:
    rows = [
        {"strategy": "a", "status": "ok", "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 2.0},
        {"strategy": "a", "status": "ok", "edge_cut": 12, "balance_error": 0.0, "runtime_seconds": 4.0},
        {"strategy": "b", "status": "ok", "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 1.0},
    ]
    summary = _summarize_graph(rows, ("a", "b"))
    assert summary["best_quality"] == "b"
    assert summary["strategies"]["a"]["edge_cut"] == 11
    assert summary["strategies"]["a"]["relative_quality_gap"] == pytest.approx(0.1)
    assert summary["strategies"]["b"]["runtime_ratio_to_graph_median"] == pytest.approx(0.5)


def test_aggregate_uses_graphs_as_the_unit_of_analysis() -> None:
    graph_summaries = {
        "g1": {"strategies": {"a": {"relative_quality_gap": 0.0, "runtime_ratio_to_graph_median": 1.0}}},
        "g2": {"strategies": {"a": {"relative_quality_gap": 0.2, "runtime_ratio_to_graph_median": 2.0}}},
    }
    aggregate = _aggregate_graph_summaries(graph_summaries, ("a",))
    assert aggregate["a"]["graphs_evaluated"] == 2
    assert aggregate["a"]["mean_relative_quality_gap"] == pytest.approx(0.1)
    assert aggregate["a"]["mean_runtime_ratio_to_graph_median"] == pytest.approx(1.5)