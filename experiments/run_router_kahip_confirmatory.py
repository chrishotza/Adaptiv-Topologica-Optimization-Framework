from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from experiments.run_cross_corpus_transfer import _load_corpora
from experiments.run_kahip_validation import (
    STRATEGY as KAHIP_STRATEGY,
    kahip_balanced_partition,
)
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY
from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_metis_confirmatory import _benchmark_graph_with_metis
from experiments.run_router_scaling_ablation import _run_config, _mean


EXPECTED_BASE_STRATEGY_COUNT = 8
EXPECTED_EXPANDED_STRATEGY_COUNT = 9


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _benchmark_graph_with_kahip(
    graph: nx.Graph,
    *,
    corpus: str,
    name: str,
    seeds: tuple[int, ...],
    iterations: int,
) -> dict:
    baseline = _benchmark_graph_with_metis(
        graph,
        corpus=corpus,
        name=name,
        seeds=seeds,
        iterations=iterations,
    )
    kahip_rows = [
        {
            "seed": seed,
            **kahip_balanced_partition(graph, seed=seed),
        }
        for seed in seeds
    ]

    strategy_means = dict(baseline["strategy_means"])
    strategy_means[KAHIP_STRATEGY] = _mean(
        row["edge_cut"] for row in kahip_rows
    )

    expected = set(baseline["strategy_means"]) | {KAHIP_STRATEGY}
    if len(baseline["strategy_means"]) != EXPECTED_BASE_STRATEGY_COUNT:
        raise AssertionError(
            f"expected 8 baseline strategies, got {len(baseline['strategy_means'])}"
        )
    if set(strategy_means) != expected:
        raise AssertionError(f"unexpected strategy set: {sorted(strategy_means)}")
    if len(strategy_means) != EXPECTED_EXPANDED_STRATEGY_COUNT:
        raise AssertionError(
            f"expected 9 expanded strategies, got {len(strategy_means)}"
        )
    if METIS_STRATEGY not in strategy_means:
        raise AssertionError("METIS strategy missing from nine-strategy comparison")

    oracle_strategy = min(
        strategy_means,
        key=lambda strategy: (strategy_means[strategy], strategy),
    )
    kahip_mean = strategy_means[KAHIP_STRATEGY]
    best_other = min(
        value
        for strategy, value in strategy_means.items()
        if strategy != KAHIP_STRATEGY
    )

    if kahip_mean < best_other:
        outcome = "strict_win"
    elif kahip_mean == best_other:
        outcome = "tie_min"
    else:
        outcome = "loss"

    return {
        **baseline,
        "strategy_means": strategy_means,
        "oracle_strategy": oracle_strategy,
        "kahip_seed_results": kahip_rows,
        "kahip_mean_edge_cut": kahip_mean,
        "kahip_vs_other_outcome": outcome,
    }


def run_kahip_confirmatory(
    output_path: str | Path = (
        "results/generalization/router_kahip_confirmatory.json"
    ),
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError("The KaHIP confirmatory protocol requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()

    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    records = {
        corpus: {
            name: _benchmark_graph_with_kahip(
                graph,
                corpus=corpus,
                name=name,
                seeds=seeds,
                iterations=iterations,
            )
            for name, graph in graphs.items()
        }
        for corpus, graphs in corpora.items()
    }

    configs = {
        name: _run_config(records, *config)
        for name, config in LOCKED_CONFIGS.items()
    }

    first_record = next(
        record
        for corpus_graphs in records.values()
        for record in corpus_graphs.values()
    )
    expanded_strategies = set(first_record["strategy_means"])
    base_strategies = sorted(expanded_strategies - {KAHIP_STRATEGY})

    if len(base_strategies) != EXPECTED_BASE_STRATEGY_COUNT:
        raise AssertionError(
            f"expected 8 base strategies, got {len(base_strategies)}"
        )
    if METIS_STRATEGY not in base_strategies:
        raise AssertionError("METIS missing from base strategy set")
    if len(expanded_strategies) != EXPECTED_EXPANDED_STRATEGY_COUNT:
        raise AssertionError(
            f"expected 9 expanded strategies, got {len(expanded_strategies)}"
        )

    oracle_distribution = {
        corpus: dict(
            Counter(
                record["oracle_strategy"]
                for record in graphs.values()
            )
        )
        for corpus, graphs in records.items()
    }

    kahip_outcomes = {
        corpus: dict(
            Counter(
                record["kahip_vs_other_outcome"]
                for record in graphs.values()
            )
        )
        for corpus, graphs in records.items()
    }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "locked leave-one-corpus-out router comparison with an expanded "
            "nine-strategy candidate set including METIS and KaHIP"
        ),
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "base_strategy_count": EXPECTED_BASE_STRATEGY_COUNT,
        "expanded_strategy_count": EXPECTED_EXPANDED_STRATEGY_COUNT,
        "base_strategies": base_strategies,
        "added_strategies": [METIS_STRATEGY, KAHIP_STRATEGY],
        "oracle_distribution": oracle_distribution,
        "kahip_outcomes": kahip_outcomes,
        "locked_configs": {
            name: {
                "features": list(config[0]),
                "scale_mode": config[1],
                "metric": config[2],
            }
            for name, config in LOCKED_CONFIGS.items()
        },
        "configs": configs,
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "protocol_controls": [
            "The feature groups, scaling modes, metric choices, seeds, and refinement iterations are unchanged from the locked METIS confirmatory protocol.",
            "The candidate set expands from eight to nine strategies solely by adding the independently validated KaHIP multilevel partitioning baseline.",
            "METIS and KaHIP use their independently validated exact-balance repair procedures and repaired edge cuts are the benchmark values.",
            "For each held-out corpus, graph-level oracle labels are learned only from the other two corpora.",
            "The majority control is recomputed from the training-corpus oracle labels and remains mandatory.",
            "No feature, scaler, metric, or router hyperparameter is tuned on this run.",
            "This run is confirmatory only and does not change the public/default router.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_kahip_confirmatory()
    print(
        json.dumps(
            {name: value["macro"] for name, value in result["configs"].items()},
            indent=2,
        )
    )
