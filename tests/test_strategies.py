import networkx as nx

from atof.strategies import BLOCReloc


def test_hybrid_period_path_preserves_balance():
    graph = nx.cycle_graph(20)
    result = BLOCReloc(graph, k=4, seed=7).refine(
        iterations=2,
        hybrid_period=1,
        hybrid_samples=50,
    )

    assert result.balance_error == 0.0
    assert result.edge_cut >= 0
