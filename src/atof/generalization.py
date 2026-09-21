from __future__ import annotations

from collections.abc import Iterable, Mapping


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
            "learned_oracle_agreement": 0.0,
            "global_oracle_agreement": 0.0,
            "heuristic_oracle_agreement": 0.0,
            "learned_mean_absolute_regret": 0.0,
            "global_mean_absolute_regret": 0.0,
            "heuristic_mean_absolute_regret": 0.0,
            "learned_mean_relative_regret": 0.0,
            "global_mean_relative_regret": 0.0,
            "heuristic_mean_relative_regret": 0.0,
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

    return {
        "corpus": corpus,
        "graphs": len(rows),
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
    }


def summarize_generalization(
    corpora: Mapping[str, Iterable[Mapping]],
) -> dict:
    """Aggregate held-out routing performance across independent graph corpora.

    Corpora are first summarized independently, then combined in two ways:
    micro averages weight every held-out graph equally; macro averages weight
    every corpus equally. This keeps a large corpus from silently dominating
    a cross-corpus summary.
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

    micro_learned_agreement = _mean(
        float(row["learned_strategy"] == row["oracle_strategy"])
        for row in all_folds
    )

    return {
        "corpus_count": len(nonempty),
        "graph_count": len(all_folds),
        "corpora": summaries,
        "micro": {
            "learned_oracle_agreement": micro_learned_agreement,
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
                "heuristic_relative_regret"
            ),
        },
        "macro": {
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
        },
    }
