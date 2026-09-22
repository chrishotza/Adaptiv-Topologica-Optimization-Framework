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


def test_trace_exposes_marginal_local_and_hybrid_gains():
    graph = nx.cycle_graph(20)
    result = BLOCReloc(graph, k=2, seed=11).refine(
        iterations=3,
        hybrid_period=1,
        hybrid_samples=20,
    )

    assert len(result.trace) == 3
    for event in result.trace:
        assert "local_gain" in event
        assert "local_work" in event
        assert "local_gain_per_work" in event
        assert "hybrid_gain" in event
        assert "hybrid_work" in event
        assert "hybrid_gain_per_work" in event
        assert "total_gain" in event
        assert event["total_gain"] >= -1e-12


def test_bloc_reloco_marginal_policy_records_budget_trace():
    import networkx as nx
    from atof.strategies import BLOCReloc

    graph = nx.cycle_graph(24)
    result = BLOCReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=8,
        hybrid_period=2,
        hybrid_samples=20,
        hybrid_policy="marginal",
        hybrid_patience=1,
    )

    assert result.balance_error == 0.0
    hybrid_events = [
        event for event in result.trace if int(event["hybrid"]) == 1
    ]
    assert hybrid_events
    assert all(int(event["hybrid_samples"]) > 0 for event in hybrid_events)
    assert all("local_gain_per_work" in event for event in result.trace)
    assert all("hybrid_gain_per_work" in event for event in result.trace)
