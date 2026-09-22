from __future__ import annotations

import networkx as nx
import pytest

from experiments.run_dynamic_compute_external_benchmark import (
    POLICIES,
    _expected_balance_error,
    _validate_exact_balance_error,
    _corpus_comparison,
    _dominance_vs_fixed,
    _policy_summary,
    _run_policy,
)


def test_external_dynamic_policy_surface_is_locked() -> None:
    assert POLICIES == ("off", "fixed", "adaptive", "marginal")


def test_exact_balance_contract():
    class GraphStub:
        def number_of_nodes(self):
            return 15

    expected = _expected_balance_error(GraphStub(), 2)
    assert expected == pytest.approx(1 / 15)
    assert _validate_exact_balance_error(GraphStub(), 2, expected)
    assert not _validate_exact_balance_error(GraphStub(), 2, expected + 0.01)


def test_run_policy_records_structural_work() -> None:
    result = _run_policy(
        nx.path_graph(30),
        seed=42,
        policy="adaptive",
    )
    assert result["edge_cut"] >= 0
    assert result["total_work"] > 0
    assert result["probe_work"] >= 0
    assert result["total_work"] >= result["probe_work"]


def test_corpus_comparison_is_graph_level():
    rows = [
        {"corpus": "a", "graph_id": "a/g1", "strategy": "fixed", "edge_cut": 10, "total_work": 100},
        {"corpus": "a", "graph_id": "a/g1", "strategy": "fixed", "edge_cut": 12, "total_work": 120},
        {"corpus": "a", "graph_id": "a/g1", "strategy": "marginal", "edge_cut": 9, "total_work": 90},
        {"corpus": "a", "graph_id": "a/g1", "strategy": "marginal", "edge_cut": 11, "total_work": 110},
    ]
    result = _corpus_comparison(rows, "marginal")
    assert result["a"]["graphs"] == 1
    assert result["a"]["mean_edge_cut_delta"] == pytest.approx(-1.0)
    assert result["a"]["mean_total_work_delta"] == pytest.approx(-10.0)
    assert result["a"]["joint_quality_work_dominance_rate"] == pytest.approx(1.0)


def test_policy_summary_counts_graphs_and_rows() -> None:
    rows = [
        {"graph_id": "g1", "strategy": "fixed", "edge_cut": 10, "total_work": 100, "runtime_seconds": 1.0, "hybrid_passes": 2, "probe_work": 0},
        {"graph_id": "g1", "strategy": "fixed", "edge_cut": 12, "total_work": 120, "runtime_seconds": 1.2, "hybrid_passes": 2, "probe_work": 0},
    ]
    summary = _policy_summary(rows, "fixed")
    assert summary["graphs"] == 1
    assert summary["rows"] == 2
    assert summary["mean_edge_cut"] == pytest.approx(11.0)
    assert summary["mean_total_work"] == pytest.approx(110.0)


def test_dominance_requires_quality_and_work_noninferiority() -> None:
    rows = [
        {"graph_id": "g1", "strategy": "fixed", "edge_cut": 10, "total_work": 100},
        {"graph_id": "g1", "strategy": "fixed", "edge_cut": 14, "total_work": 140},
        {"graph_id": "g2", "strategy": "fixed", "edge_cut": 10, "total_work": 100},
        {"graph_id": "g2", "strategy": "fixed", "edge_cut": 10, "total_work": 100},
        {"graph_id": "g1", "strategy": "adaptive", "edge_cut": 10, "total_work": 80},
        {"graph_id": "g1", "strategy": "adaptive", "edge_cut": 10, "total_work": 80},
        {"graph_id": "g2", "strategy": "adaptive", "edge_cut": 9, "total_work": 120},
        {"graph_id": "g2", "strategy": "adaptive", "edge_cut": 11, "total_work": 80},
    ]
    summary = _dominance_vs_fixed(rows, "adaptive")
    assert summary["dominates_fixed"] == 1
    assert summary["work_strictly_lower"] == 1
    assert summary["quality_strictly_better"] == 1
