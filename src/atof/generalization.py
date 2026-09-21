from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from math import log


def _mean(values: Iterable[float]) -> float:
    values = [float(value) for value in values]
    return sum(values) / len(values) if values else 0.0


def _agreement(folds: list[Mapping], selected_key: str) -> float:
    if not folds:
        return 0.0
    return sum(
        str(row[selected_key]) == str(row["oracle_strategy"])
        for row in folds
    ) / len(folds)


def _oracle_diagnostics(rows: list[Mapping]) -> dict:
    counts = Counter(str(row["oracle_strategy"]) for row in rows)
    total = len(rows)
    entropy = (
        -sum(
            (count / total) * log(count / total)
            for count in counts.values()
            if count
        )
        if total
        else 0.0
    )
    maximum_entropy = log(len(counts)) if len(counts) > 1 else 0.0

    return {
        "oracle_strategy_counts": dict(sorted(counts.items())),
        "unique_oracle_strategies": len(counts),
        "oracle_entropy": entropy,
        "oracle_normalized_entropy": (
            entropy / maximum_entropy if maximum_entropy else 0.0
        ),
    }


def summarize_routing_folds(
    folds: Iterable[Mapping],
    *,
    corpus: str | None = None,
) -> dict:
    """Summarize graph-level routing folds without treating seeds as samples."""
    rows = [dict(row) for row in folds]
    if not rows:
        return {
            "corpus": corpus,
            "graphs": 0,
            "oracle_strategy_counts": {},
            "unique_oracle_strategies": 0,
            "oracle_entropy": 0.0,
            "oracle_normalized_entropy": 0.0,
            "learned_oracle_agreement": 0.0,
            "global_oracle_agreement": 0.0,
            "heuristic_oracle_agreement": 0.0,
            "learned_mean_absolute_regret": 0.0,
            "global_mean_absolute_regret": 0.0,
            "heuristic_mean_absolute_regret": 0.0,
            "learned_mean_relative_regret": 0.0,
            "global_mean_relative_regret": 0.0,
            "heuristic_mean_relative_regret": 0.0,
            "learned_better_than_global_rate": 0.0,
            "learned_worse_than_global_rate": 0.0,
            "learned_equal_global_rate": 0.0,
            "learned_minus_global_mean_relative_regret": 0.0,
        }

    required = {
        "oracle_strategy",
        "learned_strategy",
        "global_strategy",
        "heuristic_strategy",
        "learned_absolute_regret",
        "global_absolute_regret",
        "heuristic_absolute_regret",
        "learned_relative_regret",
        "global_relative_regret",
        "heuristic_relative_regret",
    }
    missing = sorted(required.difference(rows[0]))
    if missing:
        raise ValueError(
            "routing folds are missing required fields: "
            + ", ".join(missing)
        )

    diagnostics = _oracle_diagnostics(rows)
    learned_minus_global = [
        float(row["learned_relative_regret"])
        - float(row["global_relative_regret"])
        for row in rows
    ]

    return {
        "corpus": corpus,
        "graphs": len(rows),
        **diagnostics,
        "learned_oracle_agreement": _agreement(rows, "learned_strategy"),
        "global_oracle_agreement": _agreement(rows, "global_strategy"),
        "heuristic_oracle_agreement": _agreement(rows, "heuristic_strategy"),
        "learned_mean_absolute_regret": _mean(
            row["learned_absolute_regret"] for row in rows
        ),
        "global_mean_absolute_regret": _mean(
            row["global_absolute_regret"] for row in rows
        ),
        "heuristic_mean_absolute_regret": _mean(
            row["heuristic_absolute_regret"] for row in rows
        ),
        "learned_mean_relative_regret": _mean(
            row["learned_relative_regret"] for row in rows
        ),
        "global_mean_relative_regret": _mean(
            row["global_relative_regret"] for row in rows
        ),
        "heuristic_mean_relative_regret": _mean(
            row["heuristic_relative_regret"] for row in rows
        ),
        "learned_better_than_global_rate": _mean(
            float(
                float(row["learned_relative_regret"])
                < float(row["global_relative_regret"])
            )
            for row in rows
        ),
        "learned_worse_than_global_rate": _mean(
            float(
                float(row["learned_relative_regret"])
                > float(row["global_relative_regret"])
            )
            for row in rows
        ),
        "learned_equal_global_rate": _mean(
            float(
                float(row["learned_relative_regret"])
                == float(row["global_relative_regret"])
            )
            for row in rows
        ),
        "learned_minus_global_mean_relative_regret": _mean(learned_minus_global),
    }


def summarize_transfer_folds(
    folds: Iterable[Mapping],
    *,
    test_corpus: str | None = None,
) -> dict:
    """Summarize true leave-one-corpus-out transfer folds."""
    rows = [dict(row) for row in folds]
    if not rows:
        return {
            "test_corpus": test_corpus,
            "graphs": 0,
            "oracle_strategy_counts": {},
            "unique_oracle_strategies": 0,
            "learned_oracle_agreement": 0.0,
            "majority_oracle_agreement": 0.0,
            "heuristic_oracle_agreement": 0.0,
            "learned_mean_absolute_regret": 0.0,
            "majority_mean_absolute_regret": 0.0,
            "heuristic_mean_absolute_regret": 0.0,
            "learned_mean_relative_regret": 0.0,
            "majority_mean_relative_regret": 0.0,
            "heuristic_mean_relative_regret": 0.0,
            "learned_minus_majority_mean_relative_regret": 0.0,
        }

    required = {
        "oracle_strategy",
        "learned_strategy",
        "majority_strategy",
        "heuristic_strategy",
        "learned_absolute_regret",
        "majority_absolute_regret",
        "heuristic_absolute_regret",
        "learned_relative_regret",
        "majority_relative_regret",
        "heuristic_relative_regret",
    }
    missing = sorted(required.difference(rows[0]))
    if missing:
        raise ValueError(
            "transfer folds are missing required fields: "
            + ", ".join(missing)
        )

    diagnostics = _oracle_diagnostics(rows)
    return {
        "test_corpus": test_corpus,
        "graphs": len(rows),
        "oracle_strategy_counts": diagnostics["oracle_strategy_counts"],
        "unique_oracle_strategies": diagnostics["unique_oracle_strategies"],
        "learned_oracle_agreement": _agreement(rows, "learned_strategy"),
        "majority_oracle_agreement": _agreement(
            rows, "majority_strategy"
        ),
        "heuristic_oracle_agreement": _agreement(
            rows, "heuristic_strategy"
        ),
        "learned_mean_absolute_regret": _mean(
            row["learned_absolute_regret"] for row in rows
        ),
        "majority_mean_absolute_regret": _mean(
            row["majority_absolute_regret"] for row in rows
        ),
        "heuristic_mean_absolute_regret": _mean(
            row["heuristic_absolute_regret"] for row in rows
        ),
        "learned_mean_relative_regret": _mean(
            row["learned_relative_regret"] for row in rows
        ),
        "majority_mean_relative_regret": _mean(
            row["majority_relative_regret"] for row in rows
        ),
        "heuristic_mean_relative_regret": _mean(
            row["heuristic_relative_regret"] for row in rows
        ),
        "learned_minus_majority_mean_relative_regret": _mean(
            float(row["learned_relative_regret"])
            - float(row["majority_relative_regret"])
            for row in rows
        ),
    }


def summarize_generalization(
    corpora: Mapping[str, Iterable[Mapping]],
) -> dict:
    """Aggregate held-out routing performance across independent graph corpora.

    Corpora are first summarized independently, then combined in two ways:
    micro averages weight every held-out graph equally; macro averages weight
    every corpus equally.
    """
    corpus_rows = {
        str(name): [dict(row) for row in folds]
        for name, folds in corpora.items()
    }
    summaries = {
        name: summarize_routing_folds(rows, corpus=name)
        for name, rows in corpus_rows.items()
    }
    nonempty = [item for item in summaries.values() if item["graphs"]]
    all_folds = [
        row
        for rows in corpus_rows.values()
        for row in rows
    ]

    def mean_field(field: str) -> float:
        return _mean(row[field] for row in all_folds)

    def corpus_mean(field: str) -> float:
        return _mean(item[field] for item in nonempty)

    micro = {
        "learned_oracle_agreement": _mean(
            float(row["learned_strategy"] == row["oracle_strategy"])
            for row in all_folds
        ),
        "global_oracle_agreement": _mean(
            float(row["global_strategy"] == row["oracle_strategy"])
            for row in all_folds
        ),
        "heuristic_oracle_agreement": _mean(
            float(row["heuristic_strategy"] == row["oracle_strategy"])
            for row in all_folds
        ),
        "learned_mean_absolute_regret": mean_field(
            "learned_absolute_regret"
        ),
        "global_mean_absolute_regret": mean_field(
            "global_absolute_regret"
        ),
        "heuristic_mean_absolute_regret": mean_field(
            "heuristic_absolute_regret"
        ),
        "learned_mean_relative_regret": mean_field(
            "learned_relative_regret"
        ),
        "global_mean_relative_regret": mean_field(
            "global_relative_regret"
        ),
        "heuristic_mean_relative_regret": mean_field(
            "heuristic_mean_relative_regret"
        ),
        "learned_better_than_global_rate": mean_field(
            "learned_better_than_global_rate"
        ),
        "learned_worse_than_global_rate": mean_field(
            "learned_worse_than_global_rate"
        ),
        "learned_equal_global_rate": mean_field(
            "learned_equal_global_rate"
        ),
        "learned_minus_global_mean_relative_regret": mean_field(
            "learned_minus_global_mean_relative_regret"
        ),
    }

    macro = {
        "learned_oracle_agreement": corpus_mean(
            "learned_oracle_agreement"
        ),
        "global_oracle_agreement": corpus_mean(
            "global_oracle_agreement"
        ),
        "heuristic_oracle_agreement": corpus_mean(
            "heuristic_oracle_agreement"
        ),
        "learned_mean_absolute_regret": corpus_mean(
            "learned_mean_absolute_regret"
        ),
        "global_mean_absolute_regret": corpus_mean(
            "global_mean_absolute_regret"
        ),
        "heuristic_mean_absolute_regret": corpus_mean(
            "heuristic_mean_absolute_regret"
        ),
        "learned_mean_relative_regret": corpus_mean(
            "learned_mean_relative_regret"
        ),
        "global_mean_relative_regret": corpus_mean(
            "global_mean_relative_regret"
        ),
        "heuristic_mean_relative_regret": corpus_mean(
            "heuristic_mean_relative_regret"
        ),
        "learned_better_than_global_rate": corpus_mean(
            "learned_better_than_global_rate"
        ),
        "learned_worse_than_global_rate": corpus_mean(
            "learned_worse_than_global_rate"
        ),
        "learned_equal_global_rate": corpus_mean(
            "learned_equal_global_rate"
        ),
        "learned_minus_global_mean_relative_regret": corpus_mean(
            "learned_minus_global_mean_relative_regret"
        ),
    }

    return {
        "corpus_count": len(nonempty),
        "graph_count": len(all_folds),
        "corpora": summaries,
        "micro": micro,
        "macro": macro,
    }
