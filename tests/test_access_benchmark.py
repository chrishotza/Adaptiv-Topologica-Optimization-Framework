import networkx as nx

from experiments.run_access_benchmark import build_graph, partition_for


def test_build_graph_is_deterministic():
    first = build_graph()
    second = build_graph()
    assert list(first.edges()) == list(second.edges())


def test_atof_partition_returns_machine_readable_result():
    graph = nx.path_graph(10)
    result, _ = partition_for("atof", graph, seed=42)
    assert result["edge_cut"] >= 0
    assert result["balance_error"] == 0.0
    assert len(result["partition"]) == 10


def test_networkx_partition_returns_machine_readable_result():
    graph = nx.path_graph(10)
    result, _ = partition_for("networkx", graph, seed=42)
    assert result["edge_cut"] >= 0
    assert result["balance_error"] >= 0.0
    assert len(result["partition"]) == 10


def test_atof_partition_is_seed_deterministic():
    graph = nx.karate_club_graph()
    first, _ = partition_for("atof", graph, seed=42)
    second, _ = partition_for("atof", graph, seed=42)
    assert first == second


def test_atof_portfolio_returns_machine_readable_result():
    graph = nx.karate_club_graph()
    result, _ = partition_for("atof_portfolio", graph, seed=42)
    assert result["edge_cut"] >= 0
    assert result["balance_error"] == 0.0
    assert len(result["partition"]) == 34
    assert result["selected_backend"]
