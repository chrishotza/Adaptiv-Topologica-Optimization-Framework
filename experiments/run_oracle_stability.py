from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import Counter

from atof.strategies import BLOCReloc
from experiments.run_canonical import (
    balanced_round_robin,
    kernighan_lin,
    random_balanced,
    spectral_bisection,
    spectral_modularity_bisection,
)
from experiments.run_cross_corpus_transfer import _load_corpora


STRATEGIES = (
    "round_robin",
    "random_balanced",
    "bloc_reloc_baseline",
    "bloc_reloc_affinity",
    "spectral_bisection",
    "spectral_modularity_bisection",
    "kernighan_lin",
)


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _strategy_seed_results(
    graph,
    *,
    k: int,
    seeds: tuple[int, ...],
    iterations: int,
) -> dict[str, list[float]]:
    results = {strategy: [] for strategy in STRATEGIES}
    for seed in seeds:
        results["round_robin"].append(float(balanced_round_robin(graph, k)["edge_cut"]))
        results["random_balanced"].append(
            float(random_balanced(graph, k, seed)["edge_cut"])
        )

        for variant, name in (
            ("baseline", "bloc_reloc_baseline"),
            ("affinity", "bloc_reloc_affinity"),
        ):
            result = BLOCReloc(
                graph,
                k=k,
                seed=seed,
                variant=variant,
            ).refine(iterations=iterations)
            results[name].append(float(result.edge_cut))

        results["spectral_bisection"].append(
            float(spectral_bisection(graph)["edge_cut"])
        )
        results["spectral_modularity_bisection"].append(
            float(spectral_modularity_bisection(graph)["edge_cut"])
        )
        results["kernighan_lin"].append(
            float(kernighan_lin(graph, seed)["edge_cut"])
        )
    return results


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def summarize_graph_stability(
    strategy_seed_results: dict[str, list[float]],
    *,
    seeds: tuple[int, ...],
) -> dict:
    means = {
        strategy: _mean(values)
        for strategy, values in strategy_seed_results.items()
    }
    ranking = sorted(means, key=lambda strategy: (means[strategy], strategy))
    oracle = ranking[0]
    runner_up = ranking[1] if len(ranking) > 1 else None
    oracle_mean = means[oracle]
    runner_up_mean = means[runner_up] if runner_up is not None else oracle_mean
    absolute_margin = runner_up_mean - oracle_mean
    relative_margin = absolute_margin / oracle_mean if oracle_mean else 0.0

    seed_winners: list[str] = []
    for index, _seed in enumerate(seeds):
        seed_winners.append(
            min(
                means,
                key=lambda strategy: (
                    strategy_seed_results[strategy][index],
                    strategy,
                ),
            )
        )

    oracle_seed_wins = seed_winners.count(oracle)
    consensus = oracle_seed_wins / len(seed_winners) if seed_winners else 0.0

    return {
        "strategy_means": means,
        "oracle_strategy": oracle,
        "runner_up_strategy": runner_up,
        "oracle_absolute_margin": absolute_margin,
        "oracle_relative_margin": relative_margin,
        "seed_winners": seed_winners,
        "oracle_seed_wins": oracle_seed_wins,
        "seed_consensus": consensus,
        "oracle_wins_all_seeds": bool(seed_winners) and oracle_seed_wins == len(seed_winners),
        "oracle_wins_majority_of_seeds": (
            bool(seed_winners) and oracle_seed_wins > len(seed_winners) / 2
        ),
    }


def summarize_corpus_stability(graphs: dict[str, dict]) -> dict:
    graph_values = list(graphs.values())
    oracle_counts = Counter(item["oracle_strategy"] for item in graph_values)
    consensus_values = [item["seed_consensus"] for item in graph_values]
    margins = [item["oracle_relative_margin"] for item in graph_values]

    return {
        "graphs": len(graph_values),
        "oracle_strategy_counts": dict(sorted(oracle_counts.items())),
        "unique_oracle_strategies": len(oracle_counts),
        "mean_seed_consensus": _mean(consensus_values),
        "graphs_winning_all_seeds": sum(
            item["oracle_wins_all_seeds"] for item in graph_values
        ),
        "graphs_winning_majority_of_seeds": sum(
            item["oracle_wins_majority_of_seeds"] for item in graph_values
        ),
        "mean_oracle_relative_margin": _mean(margins),
        "median_oracle_relative_margin": (
            sorted(margins)[len(margins) // 2] if margins else 0.0
        ),
    }


def run_oracle_stability(
    output_path: str = "results/generalization/oracle_stability.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir=None,
) -> dict:
    if k != 2:
        raise ValueError("The oracle stability protocol currently requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)

    studies: dict[str, dict] = {}
    for corpus, corpus_graphs in corpora.items():
        graph_results: dict[str, dict] = {}
        for name, graph in corpus_graphs.items():
            seed_results = _strategy_seed_results(
                graph,
                k=k,
                seeds=seeds,
                iterations=iterations,
            )
            summary = summarize_graph_stability(seed_results, seeds=seeds)
            graph_results[name] = {
                "corpus": corpus,
                "graph": name,
                "seeds": list(seeds),
                "strategy_seed_edge_cuts": seed_results,
                **summary,
            }

        studies[corpus] = {
            "provenance": provenance[corpus],
            "graphs": graph_results,
            "summary": summarize_corpus_stability(graph_results),
        }

    payload = {
        "schema_version": "0.1",
        "protocol": "graph-oracle seed stability and strategy-diversity analysis",
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "strategies": list(STRATEGIES),
        "corpora": studies,
        "interpretation": [
            "The graph-level oracle is the strategy with lowest mean edge cut across the configured seeds.",
            "Seed consensus measures how often that mean oracle also wins on individual seeds.",
            "Oracle margin measures how separated the winner is from the runner-up in mean edge cut.",
            "This study diagnoses target stability; it does not evaluate router generalization itself.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    from pathlib import Path

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_oracle_stability()
    print(
        json.dumps(
            {
                corpus: study["summary"]
                for corpus, study in result["corpora"].items()
            },
            indent=2,
        )
    )
