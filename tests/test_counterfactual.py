import networkx as nx

from atof.counterfactual import leave_one_family_out


def _row(graph: str, family: str, topology: dict, strategy: str, edge_cut: float) -> dict:
    return {
        "graph": graph,
        "family": family,
        "topology": topology,
        "strategy": strategy,
        "oracle_strategy": strategy,
        "edge_cut": edge_cut,
    }


def test_leave_one_family_out_has_no_graph_leakage():
    topology_a = {"density": 0.1, "avg_degree": 2.0}
    topology_b = {"density": 0.8, "avg_degree": 8.0}

    rows = [
        _row("a1", "family_a", topology_a, "alpha", 10),
        _row("a1", "family_a", topology_a, "beta", 12),
        _row("b1", "family_b", topology_b, "beta", 8),
        _row("b1", "family_b", topology_b, "alpha", 11),
    ]

    result = leave_one_family_out(
        rows,
        family_by_graph={"a1": "family_a", "b1": "family_b"},
    )

    assert result.no_lookahead is True
    assert result.family_count == 2
    assert result.graph_count == 2
    for fold in result.folds:
        assert not set(fold.train_graphs).intersection(fold.holdout_graphs)
