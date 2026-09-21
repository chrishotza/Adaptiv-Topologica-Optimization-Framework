import pytest

from atof.generalization import (
    summarize_generalization,
    summarize_routing_folds,
)


def _fold(
    oracle: str,
    learned: str,
    global_strategy: str,
    heuristic: str,
    learned_rel: float,
    global_rel: float,
    heuristic_rel: float,
) -> dict:
    return {
        "oracle_strategy": oracle,
        "learned_strategy": learned,
        "global_strategy": global_strategy,
        "heuristic_strategy": heuristic,
        "learned_absolute_regret": learned_rel * 10,
        "global_absolute_regret": global_rel * 10,
        "heuristic_absolute_regret": heuristic_rel * 10,
        "learned_relative_regret": learned_rel,
        "global_relative_regret": global_rel,
        "heuristic_relative_regret": heuristic_rel,
    }


def test_summarize_routing_folds_uses_graphs_as_units():
    folds = [
        _fold("a", "a", "b", "a", 0.0, 0.2, 0.0),
        _fold("b", "a", "b", "b", 0.1, 0.2, 0.3),
    ]

    result = summarize_routing_folds(folds, corpus="external")

    assert result["corpus"] == "external"
    assert result["graphs"] == 2
    assert result["learned_oracle_agreement"] == 0.5
    assert result["learned_mean_relative_regret"] == pytest.approx(0.05)


def test_generalization_exposes_micro_and_macro_views():
    corpora = {
        "small": [
            _fold("a", "a", "b", "b", 0.0, 0.4, 0.2),
        ],
        "larger": [
            _fold("a", "b", "b", "a", 0.3, 0.1, 0.2),
            _fold("b", "a", "b", "b", 0.1, 0.2, 0.3),
        ],
    }

    result = summarize_generalization(corpora)

    assert result["corpus_count"] == 2
    assert result["graph_count"] == 3
    assert result["micro"]["learned_mean_relative_regret"] == pytest.approx(
        0.13333333333333333
    )
    assert result["macro"]["learned_mean_relative_regret"] == pytest.approx(0.1)
