import networkx as nx

from experiments.fresh_sota_protocol import STRATEGIES, _graph_summary


def test_fresh_sota_graph_summary_requires_all_strategies_and_seeds():
    rows = []
    for strategy in STRATEGIES:
        for seed in (42, 101, 2024):
            rows.append({
                "strategy": strategy,
                "seed": seed,
                "status": "ok",
                "edge_cut": 10 if strategy == "mtkahypar_default" else 12,
                "balance_error": 0.0,
                "runtime_seconds": 1.0,
            })

    summary = _graph_summary(
        rows,
        expected_strategies=STRATEGIES,
        expected_seeds=(42, 101, 2024),
    )

    assert summary["matched"] is True
    assert summary["best_quality"] == "mtkahypar_default"
    assert summary["best_edge_cut"] == 10.0


def test_fresh_sota_graph_summary_rejects_missing_seed():
    rows = []
    for strategy in STRATEGIES:
        for seed in (42, 101):
            rows.append({
                "strategy": strategy,
                "seed": seed,
                "status": "ok",
                "edge_cut": 10,
                "balance_error": 0.0,
                "runtime_seconds": 1.0,
            })

    summary = _graph_summary(
        rows,
        expected_strategies=STRATEGIES,
        expected_seeds=(42, 101, 2024),
    )

    assert summary["matched"] is False
