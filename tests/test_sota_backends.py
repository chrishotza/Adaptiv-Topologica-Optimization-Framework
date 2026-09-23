import networkx as nx

from atof.native_backends import run_kaminpar, run_mtkahypar


def _assert_contract(result, graph, k):
    partition, edge_cut, balance = result
    assert set(partition) == set(graph)
    assert set(partition.values()) <= set(range(k))
    assert edge_cut >= 0
    assert balance == 0.0
    counts = [sum(block == i for block in partition.values()) for i in range(k)]
    assert max(counts) - min(counts) <= 1


def test_kaminpar_default_real_binding():
    import kaminpar  # noqa: F401

    graph = nx.karate_club_graph()
    _assert_contract(run_kaminpar(graph, seed=42, k=2), graph, 2)


def test_kaminpar_strong_real_binding():
    import kaminpar  # noqa: F401

    graph = nx.karate_club_graph()
    _assert_contract(run_kaminpar(graph, seed=42, k=2, quality=True), graph, 2)


def test_mtkahypar_default_real_binding():
    import mtkahypar  # noqa: F401

    graph = nx.karate_club_graph()
    _assert_contract(run_mtkahypar(graph, seed=42, k=2), graph, 2)


def test_mtkahypar_quality_real_binding():
    import mtkahypar  # noqa: F401

    graph = nx.karate_club_graph()
    _assert_contract(run_mtkahypar(graph, seed=42, k=2, quality=True), graph, 2)
