from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx

from experiments.run_cross_corpus_transfer import _benchmark_graph, _load_corpora
from experiments.run_metis_validation import STRATEGY, metis_balanced_partition
from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_scaling_ablation import _run_config, _mean


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _benchmark_graph_with_metis(
    graph: nx.Graph,
    *,
    corpus: str,
    name: str,
    seeds: tuple[int, ...],
    iterations: int,
) -> dict:
    baseline = _benchmark_graph(
        graph,
        corpus=corpus,
        name=name,
        k=2,
        seeds=seeds,
        iterations=iterations,
    )
    metis_rows = [
        metis_balanced_partition(graph, seed=seed)
        for seed in seeds
    ]
    strategy_means = dict(baseline["strategy_means"])
    strategy_means[STRATEGY] = _mean(
        row["edge_cut"] for row in metis_rows
    )
    oracle_strategy = min(
        strategy_means,
        key=lambda strategy: (strategy_means[strategy], strategy),
    )
    return {
        **baseline,
        "strategy_means": strategy_means,
        "oracle_strategy": oracle_strategy,
        "metis_seed_results": metis_rows,
    }


def run_metis_confirmatory(
    output_path: str | Path = (
        "results/generalization/router_metis_confirmatory.json"
    ),
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError("The METIS confirmatory protocol requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    records = {
        corpus: {
            name: _benchmark_graph_with_metis(
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

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "locked leave-one-corpus-out router comparison with an expanded "
            "eight-strategy candidate set including METIS"
        ),
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "base_strategy_count": 7,
        "expanded_strategy_count": 8,
        "added_strategy": STRATEGY,
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
            "The feature groups, scaling modes, metric choices, seeds, and refinement iterations are unchanged from the locked confirmatory protocol.",
            "The candidate set expands from seven to eight strategies solely by adding the independently validated METIS multilevel bisection baseline.",
            "METIS uses the independently validated exact-balance repair procedure and its repaired edge cut is the benchmark value.",
            "For each held-out corpus, all graph-level oracle labels are learned only from the other two corpora.",
            "The majority control is recomputed from the training-corpus oracle labels and remains mandatory.",
            "No new feature or router hyperparameter is tuned on this run.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    result = run_metis_confirmatory()
    print(
        json.dumps(
            {name: value["macro"] for name, value in result["configs"].items()},
            indent=2,
        )
    )
