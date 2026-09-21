from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from atof.generalization import summarize_transfer_folds
from atof.routing import LearnedTopologyRouter
from atof.selector import HeuristicRegimeSelector
from atof.snap import download_snap_dataset, snap_reference_corpus
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler
from experiments.generate_suite import build_suite
from experiments.run_canonical import (
    balanced_round_robin,
    kernighan_lin,
    random_balanced,
    spectral_bisection,
    spectral_modularity_bisection,
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


def _safe_profile(graph: nx.Graph) -> dict:
    profile = TopologyProfiler().profile(graph).to_dict()
    return {
        key: (None if isinstance(value, float) and math.isnan(value) else value)
        for key, value in profile.items()
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _benchmark_graph(
    graph: nx.Graph,
    *,
    corpus: str,
    name: str,
    k: int,
    seeds: tuple[int, ...],
    iterations: int,
) -> dict:
    selector = HeuristicRegimeSelector()
    profiler = TopologyProfiler()
    profile = profiler.profile(graph)
    topology = _safe_profile(graph)

    rows: list[dict] = []
    for seed in seeds:
        rows.append(
            {"strategy": "round_robin", "seed": seed, **balanced_round_robin(graph, k)}
        )
        rows.append(
            {"strategy": "random_balanced", "seed": seed, **random_balanced(graph, k, seed)}
        )

        for variant in ("baseline", "affinity"):
            result = BLOCReloc(
                graph,
                k=k,
                seed=seed,
                variant=variant,
            ).refine(iterations=iterations)
            rows.append(
                {
                    "strategy": f"bloc_reloc_{variant}",
                    "seed": seed,
                    "edge_cut": result.edge_cut,
                    "weighted_cost": result.weighted_cost,
                    "balance_error": result.balance_error,
                    "iterations": result.iterations,
                }
            )

        rows.append(
            {"strategy": "spectral_bisection", "seed": seed, **spectral_bisection(graph)}
        )
        rows.append(
            {"strategy": "kernighan_lin", "seed": seed, **kernighan_lin(graph, seed)}
        )

    by_strategy: dict[str, list[float]] = {}
    for row in rows:
        by_strategy.setdefault(row["strategy"], []).append(float(row["edge_cut"]))

    strategy_means = {
        strategy: _mean(values)
        for strategy, values in by_strategy.items()
    }
    oracle_strategy = min(
        strategy_means,
        key=lambda strategy: (strategy_means[strategy], strategy),
    )

    return {
        "corpus": corpus,
        "graph": name,
        "topology": topology,
        "regime": selector.classify(profile),
        "oracle_strategy": oracle_strategy,
        "strategy_means": strategy_means,
    }


def _load_corpora(
    *,
    cache_dir: str | Path | None = None,
) -> tuple[dict[str, dict[str, nx.Graph]], dict[str, dict]]:
    corpora = {
        "development": dict(build_suite()),
        "external": {},
        "snap": {},
    }
    provenance = {
        "development": {"type": "deterministic_networkx_synthetic"},
        "external": {},
        "snap": {},
    }

    from atof.datasets import standard_reference_corpus

    for dataset in standard_reference_corpus():
        graph = dataset.load()
        corpora["external"][dataset.name] = graph
        provenance["external"][dataset.name] = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "source": dataset.source,
            "reference_url": dataset.reference_url,
            "notes": dataset.notes,
        }

    for dataset in snap_reference_corpus():
        graph, metadata = download_snap_dataset(
            dataset,
            cache_dir=cache_dir,
        )
        corpora["snap"][dataset.name] = graph
        provenance["snap"][dataset.name] = metadata

    return corpora, provenance


def _choose_majority_strategy(training_graphs: list[dict]) -> str:
    counts = Counter(str(item["oracle_strategy"]) for item in training_graphs)
    if not counts:
        raise ValueError("training_graphs must not be empty")
    return min(counts, key=lambda strategy: (-counts[strategy], strategy))


def _relative_metrics(
    strategy: str,
    *,
    strategy_means: dict[str, float],
    oracle_strategy: str,
) -> tuple[float, float]:
    oracle_mean = strategy_means[oracle_strategy]
    selected_mean = strategy_means[strategy]
    absolute = selected_mean - oracle_mean
    relative = absolute / oracle_mean if oracle_mean else 0.0
    return absolute, relative


def _transfer_folds(records: dict[str, dict[str, dict]]) -> dict[str, list[dict]]:
    selector_map = {
        "hub_dominated": "bloc_reloc_affinity",
        "modular": "bloc_reloc_baseline",
        "regular_like": "bloc_reloc_baseline",
        "mixed": "bloc_reloc_baseline",
    }
    folds_by_test_corpus: dict[str, list[dict]] = {}

    for test_corpus, test_graphs in records.items():
        training_graphs = [
            record
            for corpus, graphs in records.items()
            if corpus != test_corpus
            for record in graphs.values()
        ]
        router = LearnedTopologyRouter().fit(training_graphs)
        majority_strategy = _choose_majority_strategy(training_graphs)

        folds: list[dict] = []
        for record in test_graphs.values():
            learned_strategy = router.predict(record["topology"])
            heuristic_strategy = selector_map[record["regime"]]
            oracle_strategy = record["oracle_strategy"]

            learned_abs, learned_rel = _relative_metrics(
                learned_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle_strategy,
            )
            majority_abs, majority_rel = _relative_metrics(
                majority_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle_strategy,
            )
            heuristic_abs, heuristic_rel = _relative_metrics(
                heuristic_strategy,
                strategy_means=record["strategy_means"],
                oracle_strategy=oracle_strategy,
            )

            folds.append(
                {
                    "test_corpus": test_corpus,
                    "held_out_graph": record["graph"],
                    "training_corpora": sorted(
                        corpus for corpus in records if corpus != test_corpus
                    ),
                    "training_graphs": len(training_graphs),
                    "oracle_strategy": oracle_strategy,
                    "learned_strategy": learned_strategy,
                    "majority_strategy": majority_strategy,
                    "heuristic_strategy": heuristic_strategy,
                    "learned_absolute_regret": learned_abs,
                    "majority_absolute_regret": majority_abs,
                    "heuristic_absolute_regret": heuristic_abs,
                    "learned_relative_regret": learned_rel,
                    "majority_relative_regret": majority_rel,
                    "heuristic_relative_regret": heuristic_rel,
                }
            )

        folds_by_test_corpus[test_corpus] = folds

    return folds_by_test_corpus


def run_cross_corpus_transfer(
    output_path: str | Path = "results/generalization/cross_corpus_transfer.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    """Run true leave-one-corpus-out routing transfer."""
    if k != 2:
        raise ValueError("The transfer protocol currently requires k=2.")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    records = {
        corpus: {
            name: _benchmark_graph(
                graph,
                corpus=corpus,
                name=name,
                k=k,
                seeds=seeds,
                iterations=iterations,
            )
            for name, graph in graphs.items()
        }
        for corpus, graphs in corpora.items()
    }

    folds_by_test_corpus = _transfer_folds(records)
    summaries = {
        corpus: summarize_transfer_folds(
            folds,
            test_corpus=corpus,
        )
        for corpus, folds in folds_by_test_corpus.items()
    }
    nonempty = [value for value in summaries.values() if value["graphs"]]

    macro = {
        "learned_oracle_agreement": _mean(
            [value["learned_oracle_agreement"] for value in nonempty]
        ),
        "majority_oracle_agreement": _mean(
            [value["majority_oracle_agreement"] for value in nonempty]
        ),
        "heuristic_oracle_agreement": _mean(
            [value["heuristic_oracle_agreement"] for value in nonempty]
        ),
        "learned_mean_relative_regret": _mean(
            [value["learned_mean_relative_regret"] for value in nonempty]
        ),
        "majority_mean_relative_regret": _mean(
            [value["majority_mean_relative_regret"] for value in nonempty]
        ),
        "heuristic_mean_relative_regret": _mean(
            [value["heuristic_mean_relative_regret"] for value in nonempty]
        ),
        "learned_minus_majority_mean_relative_regret": _mean(
            [
                value["learned_minus_majority_mean_relative_regret"]
                for value in nonempty
            ]
        ),
    }

    payload = {
        "schema_version": "0.1",
        "protocol": "leave-one-corpus-out routing transfer",
        "unit_of_analysis": "held-out graph",
        "created_at": time.time(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "commit_sha": _commit_sha(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "training_rule": (
            "For each test corpus, fit only on graph-level oracle labels "
            "from the other corpora."
        ),
        "transfer": {
            "folds": folds_by_test_corpus,
            "summaries": summaries,
            "macro": macro,
        },
        "limitations": [
            "This study evaluates transfer across three currently available corpus tiers, not arbitrary graph populations.",
            "The partition objective remains unweighted undirected edge cut with k=2.",
            "SNAP directed and signed semantics are normalized to the current undirected connectivity objective.",
            "The majority strategy control is based on graph-level oracle frequency in the training corpora.",
            "This is an exploratory transfer study; it does not establish universal routing generalization.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_cross_corpus_transfer()
    print(json.dumps(result["transfer"]["macro"], indent=2))
