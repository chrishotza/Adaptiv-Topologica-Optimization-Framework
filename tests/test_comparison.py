from __future__ import annotations

import networkx as nx

from atof.comparison import compare_graph, compact_comparison


def test_compare_graph_uses_identical_parameters():
    graph = nx.cycle_graph(12)
    payload = compare_graph(graph, k=3, seed=42, iterations=4)

    assert payload["schema"] == "atof.compare.v1"
    assert payload["version"] == "0.6.0"
    assert payload["mode"] == "compare"
    assert payload["graph"] == {"nodes": 12, "edges": 12}
    assert payload["parameters"] == {"k": 3, "seed": 42, "iterations": 4}
    assert payload["engine"]["schema"] == "atof.optimize.v1"
    assert payload["portfolio"]["schema"] == "atof.portfolio.v1"
    assert payload["engine"]["result"]["k"] == 3
    assert payload["portfolio"]["result"]["k"] == 3


def test_compact_comparison_keeps_machine_decision_fields():
    graph = nx.path_graph(8)
    payload = compare_graph(graph, k=2, seed=42, iterations=3)
    compact = compact_comparison(payload)

    assert compact["schema"] == "atof.compare.v1"
    assert compact["comparison"]["selection_metric"] == "observed unweighted edge_cut"
    assert compact["engine"]["result"]["edge_cut"] >= 0
    assert compact["portfolio"]["result"]["edge_cut"] >= 0
    assert "provenance" in compact
