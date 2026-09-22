import networkx as nx

from atof.strategies import BLOCReloc


def test_hybrid_ablation_pair_contract():
    graph = nx.cycle_graph(16)
    rows = []
    for variant in ("baseline", "affinity"):
        base = BLOCReloc(graph, k=2, seed=42, variant=variant).refine(iterations=5)
        hybrid = BLOCReloc(graph, k=2, seed=42, variant=variant).refine(
            iterations=5,
            hybrid_period=5,
            hybrid_samples=10,
        )
        rows.append((base, hybrid))

    assert len(rows) == 2
    for base, hybrid in rows:
        assert base.balance_error <= 0.05
        assert hybrid.balance_error <= 0.05
        assert hybrid.edge_cut >= 0
        assert hybrid.weighted_cost >= 0
