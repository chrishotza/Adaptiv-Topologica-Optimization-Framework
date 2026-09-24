from __future__ import annotations

import argparse
from math import ceil
import json
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from atof.portfolio import PortfolioCandidate, _run_metis, optimize_portfolio
from atof.routing import LearnedTopologyRouter, NearestTopologyRouter
from atof.statistics import bootstrap_mean_ci
from atof.topology import TopologyProfiler
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora

K = 4
SEEDS = (42, 101, 2024)
FEATURES = (
    "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    "clustering", "transitivity", "core_number", "diameter",
    "avg_path_length", "modularity",
)
STRATEGIES = (
    "bloc", "bloc-affinity", "metis", "kahip",
    "kaminpar", "kaminpar-strong", "mtkahypar", "mtkahypar-quality",
)
BOOTSTRAP_SEED = 2024


def _integer_feasible_imbalance(graph, k: int, *, base: float = 0.03) -> float:
    """Smallest tolerance that admits a floor/ceil integer k-way balance."""
    n = graph.number_of_nodes()
    average = n / k
    required = ceil(average) / average - 1.0
    return max(base, required)


def _postprocess_partition(graph, partition):
    from atof.portfolio import _edge_cut, _rebalance_kway
    from atof.partition import balance_error
    membership = [int(partition[node]) for node in graph.nodes()]
    repaired = _rebalance_kway(graph, membership, K)
    repaired_partition = {node: repaired[i] for i, node in enumerate(graph.nodes())}
    return repaired_partition, _edge_cut(graph, repaired_partition), balance_error(graph, repaired_partition, K)


def _pad_isolated_nodes(graph, k: int) -> tuple[object, list[object]]:
    """Pad a small graph to a k-divisible order with isolated nodes."""
    import networkx as nx

    target = max(graph.number_of_nodes(), k * k)
    if target % k:
        target += k - target % k
    padded = graph.copy()
    padding = [f"__atof_k4_padding_{i}" for i in range(target - graph.number_of_nodes())]
    while any(node in padded for node in padding):
        padding = [f"__atof_k4_padding_{i}_x" for i in range(len(padding))]
    padded.add_nodes_from(padding)
    return padded, padding


def _strip_padding(graph, partition, padding):
    stripped = {node: int(block) for node, block in partition.items() if node not in set(padding)}
    if set(stripped) != set(graph):
        raise RuntimeError("research padding changed original node coverage")
    return stripped


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _graph_record(graph, corpus: str, name: str, *, seeds: tuple[int, ...] = SEEDS) -> dict:
    profiler = TopologyProfiler()
    topology = profiler.profile(graph).to_dict()
    by_seed = {}
    strategy_means = defaultdict(list)

    retry_by_seed = {}
    for seed in seeds:
        retry_metadata = {}
        result = optimize_portfolio(
            graph, k=K, seed=seed, iterations=25, include_optional=True
        )
        candidates = {
            candidate.id: candidate
            for candidate in result.candidates
            if candidate.available and candidate.id in STRATEGIES
        }
        missing = sorted(set(STRATEGIES) - set(candidates))
        if missing:
            retry_metadata = {}
            original_errors = {
                candidate_id: next(
                    candidate.error
                    for candidate in result.candidates
                    if candidate.id == candidate_id
                )
                for candidate_id in missing
            }
            if any(candidate_id in missing for candidate_id in ("metis", "kahip")):
                padded_graph, padding_nodes = _pad_isolated_nodes(graph, K)
                backend_imbalance = _integer_feasible_imbalance(padded_graph, K)
                backend_ufactor = int(ceil(backend_imbalance * 1000))
                retry_metadata = {
                    "research_balance_tolerance": backend_imbalance,
                    "research_metis_ufactor": backend_ufactor,
                    "research_padding_nodes": len(padding_nodes),
                    "research_padding_target_nodes": padded_graph.number_of_nodes(),
                }

                if "metis" in missing:
                    try:
                        retry_started = time.perf_counter()
                        padded_partition, _, _ = _run_metis(
                            padded_graph,
                            seed=seed,
                            k=K,
                            recursive=False,
                            ufactor=backend_ufactor,
                        )
                        partition = _strip_padding(graph, padded_partition, padding_nodes)
                        partition, edge_cut, balance_error = _postprocess_partition(graph, partition)

                        candidates["metis"] = PortfolioCandidate(
                            id="metis",
                            name="METIS(PyMetis)",
                            available=True,
                            edge_cut=int(edge_cut),
                            balance_error=float(balance_error),
                            runtime_seconds=float(time.perf_counter() - retry_started),
                            partition=partition,
                            backend_version=None,
                            postprocess="balance_repair;research_isolated_node_padding",
                            error=None,
                        )
                        retry_metadata["metis_retry_count"] = 1
                        retry_metadata["metis_retry_reason"] = "fixed 3% tolerance was infeasible for integer k-way balance"
                    except Exception as exc:
                        retry_metadata["metis_retry_error"] = f"{type(exc).__name__}: {exc}"

                if "kahip" in missing:
                    try:
                        from atof.portfolio import _run_kahip
                        retry_started = time.perf_counter()
                        padded_partition, _, _ = _run_kahip(
                            padded_graph,
                            seed=seed,
                            k=K,
                            imbalance=backend_imbalance,
                        )
                        partition = _strip_padding(graph, padded_partition, padding_nodes)
                        partition, edge_cut, balance_error = _postprocess_partition(graph, partition)
                        candidates["kahip"] = PortfolioCandidate(
                            id="kahip",
                            name="KaHIP(KaFFPa-Strong)",
                            available=True,
                            edge_cut=int(edge_cut),
                            balance_error=float(balance_error),
                            runtime_seconds=float(time.perf_counter() - retry_started),
                            partition=partition,
                            backend_version=None,
                            postprocess="balance_repair;research_feasible_imbalance_retry",
                            error=None,
                        )
                        retry_metadata["kahip_retry_count"] = 1
                        retry_metadata["kahip_retry_reason"] = "fixed 3% tolerance was infeasible for integer k-way balance"
                    except Exception as exc:
                        retry_metadata["kahip_retry_error"] = f"{type(exc).__name__}: {exc}"

                missing = sorted(set(STRATEGIES) - set(candidates))
            if missing:
                raise RuntimeError(
                    f"{corpus}/{name} seed={seed}: missing k=4 candidates {missing}; "
                    f"original_errors={original_errors}; retry_metadata={retry_metadata}"
                )
        if retry_metadata:
            retry_by_seed[str(seed)] = retry_metadata
        by_seed[seed] = {
            strategy: {
                "edge_cut": int(candidates[strategy].edge_cut),
                "runtime_seconds": float(candidates[strategy].runtime_seconds),
                "balance_error": float(candidates[strategy].balance_error),
            }
            for strategy in STRATEGIES
        }
        for strategy in STRATEGIES:
            strategy_means[strategy].append(candidates[strategy].edge_cut)

    means = {strategy: _mean(values) for strategy, values in strategy_means.items()}
    oracle_strategy = min(means, key=lambda strategy: (means[strategy], strategy))
    seed_oracles = [
        min(
            by_seed[seed],
            key=lambda strategy: (by_seed[seed][strategy]["edge_cut"], strategy),
        )
        for seed in SEEDS
    ]
    return {
        "corpus": corpus,
        "graph": name,
        "graph_id": f"{corpus}/{name}",
        "topology": topology,
        "strategy_means": means,
        "oracle_strategy": oracle_strategy,
        "seed_oracles": seed_oracles,
        "stable": len(set(seed_oracles)) == 1,
        "by_seed": by_seed,
        "backend_retries": retry_by_seed,
    }


def _fit(records: list[dict]) -> LearnedTopologyRouter:
    training_rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in records
    ]
    return LearnedTopologyRouter(
        features=FEATURES, scale_mode="iqr", metric="l2"
    ).fit(training_rows)


def _evaluate(records_by_corpus: dict[str, list[dict]]) -> dict:
    folds = []
    per_graph = defaultdict(lambda: {"centroid": [], "nearest": [], "majority": []})
    oracle_hits = defaultdict(lambda: {"centroid": [], "nearest": [], "majority": []})

    for heldout, test_records in sorted(records_by_corpus.items()):
        training = [
            record
            for corpus, records in records_by_corpus.items()
            if corpus != heldout
            for record in records
        ]
        centroid = _fit(training)
        nearest = NearestTopologyRouter(features=FEATURES, scale_mode="iqr", metric="l2").fit(training)
        counts = Counter(record["oracle_strategy"] for record in training)
        majority = min(counts, key=lambda strategy: (-counts[strategy], strategy))

        fold_centroid = []
        fold_nearest = []
        fold_majority = []
        for record in test_records:
            oracle = record["oracle_strategy"]
            oracle_cut = record["strategy_means"][oracle]
            predicted = {
                "centroid": centroid.predict(record["topology"]),
                "nearest": nearest.predict(record["topology"]),
                "majority": majority,
            }
            for name, strategy in predicted.items():
                selected_cut = record["strategy_means"][strategy]
                relative = (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0
                per_graph[record["graph_id"]][name].append(relative)
                oracle_hits[record["graph_id"]][name].append(float(strategy == oracle))
            fold_centroid.append(per_graph[record["graph_id"]]["centroid"][-1])
            fold_nearest.append(per_graph[record["graph_id"]]["nearest"][-1])
            fold_majority.append(per_graph[record["graph_id"]]["majority"][-1])

        folds.append({
            "test_corpus": heldout,
            "test_graphs": len(test_records),
            "centroid_mean_relative_regret": _mean(fold_centroid),
            "nearest_mean_relative_regret": _mean(fold_nearest),
            "majority_mean_relative_regret": _mean(fold_majority),
        })

    graph_ids = sorted(per_graph)
    centroid_values = [_mean(per_graph[g]["centroid"]) for g in graph_ids]
    nearest_values = [_mean(per_graph[g]["nearest"]) for g in graph_ids]
    majority_values = [_mean(per_graph[g]["majority"]) for g in graph_ids]
    centroid_delta = [a - b for a, b in zip(centroid_values, majority_values)]
    nearest_delta = [a - b for a, b in zip(nearest_values, majority_values)]
    centroid_low, centroid_high = bootstrap_mean_ci(centroid_delta, resamples=5000, seed=BOOTSTRAP_SEED)
    nearest_low, nearest_high = bootstrap_mean_ci(nearest_delta, resamples=5000, seed=BOOTSTRAP_SEED)

    all_records = [
        record
        for corpus_records in records_by_corpus.values()
        for record in corpus_records
    ]
    unstable = [record for record in all_records if not record["stable"]]

    return {
        "graphs": len(graph_ids),
        "folds": folds,
        "macro": {
            "centroid_mean_relative_regret": _mean(centroid_values),
            "nearest_mean_relative_regret": _mean(nearest_values),
            "majority_mean_relative_regret": _mean(majority_values),
            "centroid_minus_majority_mean_relative_regret": _mean(centroid_delta),
            "nearest_minus_majority_mean_relative_regret": _mean(nearest_delta),
            "centroid_minus_majority_bootstrap_95_ci": [centroid_low, centroid_high],
            "nearest_minus_majority_bootstrap_95_ci": [nearest_low, nearest_high],
        },
        "graph_level": {
            "centroid_better_graphs": sum(value < 0 for value in centroid_delta),
            "centroid_worse_graphs": sum(value > 0 for value in centroid_delta),
            "centroid_ties": sum(value == 0 for value in centroid_delta),
            "nearest_better_graphs": sum(value < 0 for value in nearest_delta),
            "nearest_worse_graphs": sum(value > 0 for value in nearest_delta),
            "nearest_ties": sum(value == 0 for value in nearest_delta),
        },
        "oracle_agreement": {
            name: _mean([_mean(oracle_hits[g][name]) for g in graph_ids])
            for name in ("centroid", "nearest", "majority")
        },
        "seed_stability": {
            "graphs": len(all_records),
            "unstable_graphs": len(unstable),
            "unstable_graph_rate": len(unstable) / len(all_records) if all_records else 0.0,
            "seed_oracles": {
                record["graph_id"]: record["seed_oracles"]
                for record in all_records
            },
        },
    }


def run(output_path: str | Path, cache_dir: str | Path | None = None, *, seeds: tuple[int, ...] = SEEDS) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    records_by_corpus = {
        corpus: [
            _graph_record(graph, corpus, name, seeds=seeds)
            for name, graph in sorted(graphs.items())
        ]
        for corpus, graphs in sorted(corpora.items())
    }
    total_graphs = sum(len(records) for records in records_by_corpus.values())
    if total_graphs != 20:
        raise AssertionError(f"expected 20 graphs, got {total_graphs}")

    result = {
        "schema_version": "1.0",
        "protocol": "frozen k=4 leave-one-corpus-out routing generalization",
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": K,
        "seeds": list(seeds),
        "candidate_strategies": list(STRATEGIES),
        "corpora": {
            corpus: {"graphs": len(records), "provenance": provenance[corpus]}
            for corpus, records in records_by_corpus.items()
        },
        "router": {"features": list(FEATURES), "scale_mode": "iqr", "metric": "l2"},
        "evaluation": _evaluate(records_by_corpus),
        "evidence_boundary": [
            "The k=4 strategy set is fixed before evaluation and excludes the k=2-only NetworkX Kernighan-Lin backend.",
            "Topology vectors and routing parameters are frozen from the existing all-feature IQR/L2 configuration.",
            "For each held-out corpus, oracle labels are derived only from the other three corpora.",
            "The graph-level mean edge-cut oracle is evaluated over three fixed solver seeds.",
            "Tiny k=4 backend compatibility retries may add isolated padding nodes; padding nodes carry no edges and are removed before scoring the original graph.",
            "No held-out seed outcome is used to fit the router.",
            "No production/default behavior changes.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.output, args.cache_dir)
    print(json.dumps(result["evaluation"]["macro"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
