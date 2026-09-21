import pytest

from atof.generalization import summarize_transfer_folds
from experiments.run_cross_corpus_transfer import _choose_majority_strategy


def _fold(oracle, learned, majority, heuristic):
    return {
        "oracle_strategy": oracle,
        "learned_strategy": learned,
        "majority_strategy": majority,
        "heuristic_strategy": heuristic,
        "learned_absolute_regret": 0.0,
        "majority_absolute_regret": 1.0,
        "heuristic_absolute_regret": 2.0,
        "learned_relative_regret": 0.0,
        "majority_relative_regret": 0.1,
        "heuristic_relative_regret": 0.2,
    }


def test_transfer_summary_preserves_oracle_diversity_and_regret_delta():
    result = summarize_transfer_folds(
        [
            _fold("a", "a", "a", "b"),
            _fold("b", "a", "a", "b"),
            _fold("a", "a", "b", "a"),
        ],
        test_corpus="external",
    )

    assert result["graphs"] == 3
    assert result["unique_oracle_strategies"] == 2
    assert result["oracle_strategy_counts"] == {"a": 2, "b": 1}
    assert result["learned_oracle_agreement"] == 2 / 3
    assert result["majority_oracle_agreement"] == 1 / 3
    assert result["learned_minus_majority_mean_relative_regret"] == pytest.approx(-0.1)


def test_majority_strategy_has_deterministic_tie_break():
    training = [
        {"oracle_strategy": "kernighan_lin"},
        {"oracle_strategy": "bloc_reloc_baseline"},
    ]
    assert _choose_majority_strategy(training) == "bloc_reloc_baseline"
