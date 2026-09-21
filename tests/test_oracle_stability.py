import pytest

from experiments.run_oracle_stability import (
    summarize_corpus_stability,
    summarize_graph_stability,
)


def test_summarize_graph_stability_tracks_seed_consensus():
    results = {
        "alpha": [5.0, 5.0, 6.0],
        "beta": [6.0, 7.0, 5.0],
    }
    summary = summarize_graph_stability(results, seeds=(42, 101, 2024))
    assert summary["oracle_strategy"] == "alpha"
    assert summary["oracle_seed_wins"] == 2
    assert summary["seed_consensus"] == 2 / 3
    assert summary["oracle_wins_majority_of_seeds"] is True
    assert summary["oracle_absolute_margin"] == pytest.approx(2 / 3)


def test_summarize_corpus_stability_counts_oracle_diversity():
    graphs = {
        "g1": {
            "oracle_strategy": "alpha",
            "seed_consensus": 1.0,
            "oracle_wins_all_seeds": True,
            "oracle_wins_majority_of_seeds": True,
            "oracle_relative_margin": 0.10,
        },
        "g2": {
            "oracle_strategy": "beta",
            "seed_consensus": 2 / 3,
            "oracle_wins_all_seeds": False,
            "oracle_wins_majority_of_seeds": True,
            "oracle_relative_margin": 0.20,
        },
    }
    summary = summarize_corpus_stability(graphs)
    assert summary["graphs"] == 2
    assert summary["unique_oracle_strategies"] == 2
    assert summary["oracle_strategy_counts"] == {"alpha": 1, "beta": 1}
    assert summary["mean_seed_consensus"] == pytest.approx(5 / 6)
    assert summary["graphs_winning_all_seeds"] == 1
    assert summary["graphs_winning_majority_of_seeds"] == 2
