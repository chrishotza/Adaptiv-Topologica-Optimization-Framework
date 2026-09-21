from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from experiments.run_cross_corpus_transfer import _benchmark_graph, _load_corpora
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY, metis_balanced_partition
from experiments.run_router_scaling_ablation import _mean


STRATEGY = "kahip_kaffpa_strong_balanced"
BASE_STRATEGIES = (
    "round_robin",
    "random_balanced",
    "bloc_reloc_baseline",
    "bloc_reloc_affinity",
    "spectral_bisection",
    "spectral_modularity_bisection",
    "kernighan_lin",
    "metis_multilevel_balanced",
)

KAFFPA_MODE_STRONG = 2
KAFFPA_IMBALANCE = 0.03


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _cut_from_partition(graph: nx.Graph, membership: dict) -> int:
    return sum(membership[u] != membership[v] for u, v in graph.edges())


def rebalance_two_way_partition(
    graph: nx.Graph,
    membership: list[int],
) -> tuple[list[int], int]:
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


def kahip_balanced_partition(
    graph: nx.Graph,
    *,
    seed: int,
) -> dict:
    if graph.number_of_nodes() < 2:
        raise ValueError("KaHIP bisection requires at least two nodes")

    import kahip

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    xadj = [0]
    adjncy: list[int] = []

    for node in nodes:
        adjncy.extend(index[neighbor] for neighbor in graph.neighbors(node))
        xadj.append(len(adjncy))

    vwgt = [1] * len(nodes)
    adjcwgt = [1] * len(adjncy)

    raw_edge_cut, raw_blocks = kahip.kaffpa(
        vwgt,
        xadj,
        adjcwgt,
        adjncy,
        2,
        KAFFPA_IMBALANCE,
        1,
        int(seed),
        KAFFPA_MODE_STRONG,
    )
    raw_membership = [int(block) for block in raw_blocks]

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
        "raw_kahip_edge_cut": int(raw_edge_cut),
        "raw_partition_size_zero": int(raw_membership.count(0)),
        "raw_partition_size_one": int(raw_membership.count(1)),
        "repair_moves": int(repair_moves),
        "balance_error": 0.0,
        "weighted_cost": float(final_cut),
        "vertex_part": repaired_membership,
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
    kahip_rows = [
        {
            "seed": seed,
            **kahip_balanced_partition(graph, seed=seed),
        }
        for seed in seeds
    ]

    strategy_means = dict(baseline["strategy_means"])
    strategy_means[METIS_STRATEGY] = _mean(
        row["edge_cut"] for row in metis_rows
    )
    strategy_means[STRATEGY] = _mean(
        row["edge_cut"] for row in kahip_rows
    )
    expected = set(BASE_STRATEGIES) | {STRATEGY}
    if set(strategy_means) != expected:
        raise AssertionError(f"unexpected strategy set: {sorted(strategy_means)}")
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
        "metis_mean_edge_cut": strategy_means[METIS_STRATEGY],
        "kahip_seed_results": kahip_rows,
        "kahip_mean_edge_cut": strategy_means[STRATEGY],
        "kahip_wins_graph": oracle_strategy == STRATEGY,
    }


def run_kahip_validation(
    output_path: str | Path = "results/generalization/kahip_validation.json",
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
                "kahip_graph_wins": sum(
                    result["kahip_wins_graph"]
                    for result in graph_results.values()
                ),
                "kahip_mean_edge_cut": (
                    sum(result["kahip_mean_edge_cut"] for result in graph_results.values())
                    / len(graph_results)
                    if graph_results
                    else 0.0
                ),
            },
        }

    payload = {
        "schema_version": "0.2",
        "protocol": "independent KaHIP KaFFPa Strong partitioning baseline with exact-balance repair evaluated against the full METIS-expanded eight-strategy candidate set",
        "unit_of_analysis": "graph-level candidate-strategy comparison",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": 2,
        "seeds": list(seeds),
        "iterations": iterations,
        "base_strategy_count": len(BASE_STRATEGIES),
        "base_strategies": list(BASE_STRATEGIES),
        "expanded_strategy_count": len(BASE_STRATEGIES) + 1,
        "kahip_strategy": STRATEGY,
        "kahip_mode": "STRONG",
        "kahip_imbalance": KAFFPA_IMBALANCE,
        "corpora": studies,
        "interpretation": [
            "KaHIP is evaluated as an independent multilevel partitioning family after METIS.",
            "The comparison contains the full eight-strategy candidate set validated by the METIS transfer experiment, then adds KaHIP as the ninth candidate.",
            "KaFFPa Strong uses a 3% imbalance tolerance, followed by the same deterministic exact-balance repair principle used for the METIS validation.",
            "The repaired edge cut, not the raw KaHIP objective, is the comparable benchmark metric.",
            "KaHIP is not inserted into the routing model by this experiment; the purpose is to test further oracle diversification independently of METIS.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_kahip_validation()
    print(
        json.dumps(
            {
                corpus: study["summary"]
                for corpus, study in result["corpora"].items()
            },
            indent=2,
        )
    )
