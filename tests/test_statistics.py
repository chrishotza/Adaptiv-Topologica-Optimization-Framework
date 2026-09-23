from atof.statistics import bootstrap_mean_ci, paired_summary


def test_bootstrap_is_deterministic():
    values = [1.0, 2.0, 3.0, 4.0]
    first = bootstrap_mean_ci(values, resamples=250, seed=7)
    second = bootstrap_mean_ci(values, resamples=250, seed=7)
    assert first == second


def test_paired_summary_aggregates_by_graph():
    rows = [
        {"graph": "a", "seed": 1, "strategy": "A", "edge_cut": 10},
        {"graph": "a", "seed": 2, "strategy": "A", "edge_cut": 12},
        {"graph": "a", "seed": 1, "strategy": "B", "edge_cut": 14},
        {"graph": "a", "seed": 2, "strategy": "B", "edge_cut": 16},
        {"graph": "b", "seed": 1, "strategy": "A", "edge_cut": 20},
        {"graph": "b", "seed": 2, "strategy": "A", "edge_cut": 22},
        {"graph": "b", "seed": 1, "strategy": "B", "edge_cut": 18},
        {"graph": "b", "seed": 2, "strategy": "B", "edge_cut": 20},
    ]

    summary = paired_summary(
        rows,
        strategy_a="A",
        strategy_b="B",
        resamples=250,
        seed=3,
    )

    assert summary["n_graphs"] == 2
    assert summary["mean_a"] == 16.0
    assert summary["mean_b"] == 17.0
    assert summary["mean_difference_a_minus_b"] == -1.0
    assert summary["a_wins"] == 1
    assert summary["b_wins"] == 1


def test_paired_summary_preserves_corpus_identity():
    rows = [
        {"graph": "shared", "graph_id": "corpus_a/shared", "seed": 1, "strategy": "A", "edge_cut": 10},
        {"graph": "shared", "graph_id": "corpus_a/shared", "seed": 1, "strategy": "B", "edge_cut": 20},
        {"graph": "shared", "graph_id": "corpus_b/shared", "seed": 1, "strategy": "A", "edge_cut": 30},
        {"graph": "shared", "graph_id": "corpus_b/shared", "seed": 1, "strategy": "B", "edge_cut": 15},
    ]

    summary = paired_summary(
        rows,
        strategy_a="A",
        strategy_b="B",
        resamples=250,
        seed=11,
    )

    assert summary["n_graphs"] == 2
    assert summary["graphs"] == ["corpus_a/shared", "corpus_b/shared"]
    assert summary["mean_difference_a_minus_b"] == 2.5
    assert summary["a_wins"] == 1
    assert summary["b_wins"] == 1
