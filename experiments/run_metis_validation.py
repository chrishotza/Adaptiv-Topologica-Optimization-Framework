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
from experiments.run_router_scaling_ablation import _benchmark_graph


STRATEGY = "metis_multilevel_balanced"
BASE_STRATEGIES = (
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


def _cut_from_partition(graph: nx.Graph, partition: dict) -> int:
    return sum(partition[u] != partition[v] for u, v in graph.edges())


def rebalance_two_way_partition(
    graph: nx.Graph,
    membership: list[int],
) -> tuple[list[int], int]:
    """Repair a METIS two-way partition to the benchmark's exact k=2 balance."""
    if len(membership) != graph.number_of_nodes():
        raise ValueError("membership length must equal graph node count")
    if set(membership) - {0, 1}:
        raise ValueError("membership must contain only 0 and 1")

    target_zero = graph.number_of_nodes() // 2
    current_zero = membership.count(0)
    if current_zero == target_zero:
        return list(membership), 0

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    result = list(membership)
    moves = abs(current_zero - target_zero)

    source = 0 if current_zero > target_zero else 1
    target = 1 - source

    for _ in range(moves):
        candidates: list[tuple[int, str, int]] = []
        for node in nodes:
            i = index[node]
            if result[i] != source:
                continue

            source_neighbors = sum(
                1
                for neighbor in graph.neighbors(node)
                if result[index[neighbor]] == source
            )
            target_neighbors = graph.degree(node) - source_neighbors
            delta = source_neighbors - target_neighbors
            candidates.append((delta, repr(node), i))

        if not candidates:
            raise RuntimeError("could not find a source-part vertex for balance repair")

        _, _, chosen = min(candidates)
        result[chosen] = target

    if result.count(0) != target_zero:
        raise AssertionError("balance repair failed to reach the exact target")

    return result, moves


def metis_balanced_partition(
    graph: nx.Graph,
    *,
    seed: int,
) -> dict:
    """Run METIS multilevel bisection and repair to exact benchmark balance."""
    if graph.number_of_nodes() < 2:
        raise ValueError("METIS bisection requires at least two nodes")

    import pymetis

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = [
        [index[neighbor] for neighbor in graph.neighbors(node)]
        for node in nodes
    ]

    options = pymetis.Options(seed=seed)
    raw = pymetis.part_graph(
        2,
        adjacency=adjacency,
        tpwgts=[0.5, 0.5],
        recursive=True,
        options=options,
    )
    raw_membership = list(raw.vertex_part)
    raw_zero = raw_membership.count(0)

    repaired_membership, repair_moves = rebalance_two_way_partition(
        graph,
        raw_membership,
    )
    partition = {
        node: repaired_membership[index[node]]
        for node in nodes
    }
    final_cut = _cut_from_partition(graph, partition)

    return {
        "edge_cut": int(final_cut),
        "raw_metis_edge_cuts": int(raw.edge_cuts),
        "raw_partition_size_zero": int(raw_zero),
        "raw_partition_size_one": int(len(nodes) - raw_zero),
        "repair_moves": int(repair_moves),
        "balance_error": 0.0,
        "weighted_cost": float(final_cut),
    }


def summarize_graph(
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
        {
            "seed": seed,
            **metis_balanced_partition(graph, seed=seed),
        }
        for seed in seeds
    ]

    strategy_means = dict(baseline["strategy_means"])
    strategy_means[STRATEGY] = (
        sum(row["edge_cut"] for row in metis_rows) / len(metis_rows)
    )
    ranked = sorted(strategy_means.items(), key=lambda item: (item[1], item[0]))
    oracle_strategy = ranked[0][0]

    return {
        "corpus": corpus,
        "graph": name,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "strategy_means": strategy_means,
        "oracle_strategy": oracle_strategy,
        "oracle_runner_up_strategy": ranked[1][0],
        "oracle_absolute_margin": ranked[1][1] - ranked[0][1],
        "metis_seed_results": metis_rows,
        "metis_mean_edge_cut": strategy_means[STRATEGY],
        "metis_wins_graph": oracle_strategy == STRATEGY,
    }


def run_metis_validation(
    output_path: str | Path = "results/generalization/metis_validation.json",
    *,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)

    studies: dict[str, dict] = {}
    for corpus, graphs in corpora.items():
        graph_results = {
            name: summarize_graph(
                graph,
                corpus=corpus,
                name=name,
                seeds=seeds,
                iterations=iterations,
            )
            for name, graph in graphs.items()
        }
        oracle_counts = Counter(
            result["oracle_strategy"] for result in graph_results.values()
        )
        studies[corpus] = {
            "provenance": provenance[corpus],
            "graphs": graph_results,
            "summary": {
                "graphs": len(graph_results),
                "oracle_strategy_counts": dict(sorted(oracle_counts.items())),
                "metis_graph_wins": sum(
                    result["metis_wins_graph"]
                    for result in graph_results.values()
                ),
                "metis_mean_edge_cut": (
                    sum(result["metis_mean_edge_cut"] for result in graph_results.values())
                    / len(graph_results)
                    if graph_results
                    else 0.0
                ),
            },
        }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "independent METIS multilevel bisection baseline with exact-balance repair"
        ),
        "unit_of_analysis": "graph-level candidate-strategy comparison",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": 2,
        "seeds": list(seeds),
        "iterations": iterations,
        "base_strategies": list(BASE_STRATEGIES),
        "metis_strategy": STRATEGY,
        "corpora": studies,
        "interpretation": [
            "METIS is evaluated as an independent multilevel partitioning family.",
            "tpwgts targets a two-way 50/50 partition, followed by a deterministic exact-balance repair because the ATOF benchmark requires exact balance.",
            "The repaired cut, not the raw METIS objective, is the comparable benchmark metric.",
            "METIS is not inserted into the routing model by this experiment; the purpose is to test whether the candidate oracle becomes more diverse under a strong independent baseline.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_metis_validation()
    print(
        json.dumps(
            {
                corpus: study["summary"]
                for corpus, study in result["corpora"].items()
            },
            indent=2,
        )
    )
