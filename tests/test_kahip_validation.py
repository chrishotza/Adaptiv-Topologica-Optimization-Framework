import networkx as nx

from experiments.run_kahip_validation import (
    BASE_STRATEGIES,
    kahip_balanced_partition,
    summarize_graph,
)


def test_kahip_partition_reaches_exact_balance():
    graph = nx.path_graph(11)
    result = kahip_balanced_partition(graph, seed=42)

    assert result["balance_error"] == 0.0
    assert result["edge_cut"] >= 0
    assert len(result["vertex_part"]) == graph.number_of_nodes()


def test_kahip_partition_is_reproducible_for_seed():
    graph = nx.cycle_graph(20)

    first = kahip_balanced_partition(graph, seed=101)
    second = kahip_balanced_partition(graph, seed=101)

    assert first["edge_cut"] == second["edge_cut"]
    assert first["vertex_part"] == second["vertex_part"]


def test_kahip_partition_uses_two_blocks():
    graph = nx.barabasi_albert_graph(30, 2, seed=7)
    result = kahip_balanced_partition(graph, seed=2024)

    assert set(result["vertex_part"]) == {0, 1}

    
def test_kahip_comparison_includes_metis_expanded_candidate_set():
    graph = nx.cycle_graph(20)
    result = summarize_graph(
        graph,
        corpus="test",
        name="cycle20",
        seeds=(42,),
        iterations=1,
    )

    assert len(BASE_STRATEGIES) == 8
    assert "metis_multilevel_balanced" in result["strategy_means"]
    assert "kahip_kaffpa_strong_balanced" in result["strategy_means"]
    assert len(result["strategy_means"]) == 9
