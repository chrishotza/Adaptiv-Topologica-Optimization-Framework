from __future__ import annotations

import networkx as nx

from experiments.run_kway_rebalance_audit import audit_membership


def test_audit_reports_zero_repair_for_exact_partition() -> None:
    graph = nx.path_graph(8)
    membership = [0, 0, 1, 1, 2, 2, 3, 3]

    result = audit_membership(graph, membership, 4)

    assert result["repair_needed"] is False
    assert result["repair_moves"] == 0
    assert result["raw_edge_cut"] == result["repaired_edge_cut"]
    assert result["cut_delta"] == 0
    assert result["raw_within_exact_contract"] is True


def test_audit_reports_repair_delta() -> None:
    graph = nx.path_graph(8)
    membership = [0, 0, 0, 0, 0, 1, 2, 3]

    result = audit_membership(graph, membership, 4)

    assert result["repair_needed"] is True
    assert result["repair_moves"] > 0
    assert sorted(result["repaired_block_counts"]) == [2, 2, 2, 2]
    assert result["raw_edge_cut"] <= result["repaired_edge_cut"]
    assert result["cut_delta"] >= 0


def test_audit_rejects_invalid_membership_length() -> None:
    graph = nx.path_graph(8)

    try:
        audit_membership(graph, [0, 1, 2], 4)
    except ValueError as exc:
        assert "length" in str(exc)
    else:
        raise AssertionError("expected invalid membership length to fail")
