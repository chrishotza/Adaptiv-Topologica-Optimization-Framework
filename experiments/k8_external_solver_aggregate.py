from __future__ import annotations

import argparse
import gzip
import io
import json
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

from atof.routing import FEATURE_GROUPS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from atof.topology import TopologyProfiler

K = 8
TRAINING_SEEDS = (42, 101, 2024)
EXTERNAL_SEEDS = (5003, 7003, 9001, 12011, 16001)
STRATEGIES = (
    "bloc",
    "bloc-affinity",
    "metis",
    "kahip",
    "kaminpar",
    "kaminpar-strong",
    "mtkahypar",
    "mtkahypar-quality",
)

ROUTER_CONFIGS = {
    "all_iqr_l2": tuple(FEATURE_GROUPS["all"]),
    "global_paths_iqr_l2": tuple(FEATURE_GROUPS["global_paths"]),
}

DATASETS = {
    "ca_astroph": {
        "download_url": "https://snap.stanford.edu/data/ca-AstroPh.txt.gz",
        "reference_url": "https://snap.stanford.edu/data/ca-AstroPh.html",
    },
    "ca_condmat": {
        "download_url": "https://snap.stanford.edu/data/ca-CondMat.txt.gz",
        "reference_url": "https://snap.stanford.edu/data/ca-CondMat.html",
    },
}


def load_training(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["training_seeds"] != list(TRAINING_SEEDS):
        raise AssertionError("training seed grid mismatch")
    if len(data["graphs"]) != 20:
        raise AssertionError("expected 20 frozen training graphs")
    return data["graphs"]


def load_external_graph(dataset: str, cache_dir: Path) -> nx.Graph:
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = DATASETS[dataset]["download_url"]
    destination = cache_dir / url.rsplit("/", 1)[-1]
    if destination.exists():
        payload = destination.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "ATOF/0.6.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        destination.write_bytes(payload)

    graph = nx.Graph()
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        for raw in io.TextIOWrapper(stream, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                graph.add_edge(parts[0], parts[1])
    graph.remove_edges_from(nx.selfloop_edges(graph))
    return nx.convert_node_labels_to_integers(graph, ordering="default")


def fit_router(training: list[dict], features: tuple[str, ...]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in training
    ]
    return LearnedTopologyRouter(
        features=features,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)


def mean_regret(strategy_means: dict[str, float], oracle: str, selected: str) -> float:
    oracle_cut = float(strategy_means[oracle])
    selected_cut = float(strategy_means[selected])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def aggregate(input_dir: Path, training_fixture: Path, output: Path, topology_dir: Path) -> dict:
    files = sorted(input_dir.glob("*.json"))
    expected = 2 * len(EXTERNAL_SEEDS) * len(STRATEGIES)
    if len(files) != expected:
        raise AssertionError(f"expected {expected} unit files, got {len(files)}")

    by_graph = defaultdict(lambda: defaultdict(dict))
    unit_runtime = {}
    for path in files:
        item = json.loads(path.read_text(encoding="utf-8"))
        dataset = item["dataset"]
        strategy = item["strategy"]
        seed = int(item["seed"])
        result = item["result"]
        if result["error"] is not None:
            raise AssertionError(
                f"unit failed: {dataset}/{strategy}/seed={seed}: {result['error']}"
            )
        by_graph[dataset][seed][strategy] = result
        unit_runtime[f"{dataset}/{strategy}/{seed}"] = result["runtime_seconds"]

    for dataset in DATASETS:
        for seed in EXTERNAL_SEEDS:
            missing = sorted(set(STRATEGIES) - set(by_graph[dataset][seed]))
            if missing:
                raise AssertionError(f"missing {dataset} seed={seed}: {missing}")

    training = load_training(training_fixture)
    majority_counts = Counter(record["oracle_strategy"] for record in training)
    majority_strategy = min(
        majority_counts,
        key=lambda name: (-majority_counts[name], name),
    )

    router_results = {}
    graph_records = []
    for dataset in sorted(DATASETS):
        graph = load_external_graph(dataset, cache_dir)
        topology = TopologyProfiler().profile(graph).to_dict()

        strategy_means = {}
        seed_oracles = []
        by_seed = {}
        for seed in EXTERNAL_SEEDS:
            seed_rows = by_graph[dataset][seed]
            by_seed[str(seed)] = {
                strategy: {
                    "edge_cut": int(seed_rows[strategy]["edge_cut"]),
                    "balance_error": float(seed_rows[strategy]["balance_error"]),
                    "runtime_seconds": float(seed_rows[strategy]["runtime_seconds"]),
                }
                for strategy in STRATEGIES
            }
            seed_oracle = min(
                STRATEGIES,
                key=lambda strategy: (
                    by_seed[str(seed)][strategy]["edge_cut"],
                    strategy,
                ),
            )
            seed_oracles.append(seed_oracle)

        for strategy in STRATEGIES:
            strategy_means[strategy] = sum(
                by_seed[str(seed)][strategy]["edge_cut"] for seed in EXTERNAL_SEEDS
            ) / len(EXTERNAL_SEEDS)

        oracle_strategy = min(
            strategy_means,
            key=lambda strategy: (strategy_means[strategy], strategy),
        )

        router_for_graph = {}
        for name, features in ROUTER_CONFIGS.items():
            router = fit_router(training, features)
            selected = router.predict(topology)
            router_for_graph[name] = {
                "selected_strategy": selected,
                "relative_regret": mean_regret(
                    strategy_means, oracle_strategy, selected
                ),
            }

        majority_regret = mean_regret(
            strategy_means, oracle_strategy, majority_strategy
        )

        graph_records.append(
            {
                "dataset": dataset,
                "reference_url": DATASETS[dataset]["reference_url"],
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "topology": topology,
                "strategy_means": strategy_means,
                "oracle_strategy": oracle_strategy,
                "seed_oracles": seed_oracles,
                "stable_oracle": len(set(seed_oracles)) == 1,
                "by_seed": by_seed,
                "routers": router_for_graph,
                "majority_strategy": majority_strategy,
                "majority_relative_regret": majority_regret,
            }
        )

    majority_values = [
        float(record["majority_relative_regret"]) for record in graph_records
    ]
    m_low, m_high = bootstrap_mean_ci(
        majority_values, resamples=5000, seed=2024
    )

    routers = {}
    paired = {}
    for router_name in ROUTER_CONFIGS:
        values = [
            float(record["routers"][router_name]["relative_regret"])
            for record in graph_records
        ]
        low, high = bootstrap_mean_ci(values, resamples=5000, seed=2024)
        routers[router_name] = {
            "graphs": len(values),
            "mean_relative_regret": sum(values) / len(values),
            "bootstrap_95_ci": [low, high],
            "graph_values": {
                record["dataset"]: value
                for record, value in zip(graph_records, values)
            },
        }

        diffs = [
            float(record["routers"][router_name]["relative_regret"])
            - float(record["majority_relative_regret"])
            for record in graph_records
        ]
        d_low, d_high = bootstrap_mean_ci(diffs, resamples=5000, seed=2024)
        paired[router_name] = {
            "mean_router_minus_majority": sum(diffs) / len(diffs),
            "bootstrap_95_ci": [d_low, d_high],
            "router_better_graphs": sum(value < 0 for value in diffs),
            "router_worse_graphs": sum(value > 0 for value in diffs),
            "ties": sum(value == 0 for value in diffs),
            "graph_values": {
                record["dataset"]: value
                for record, value in zip(graph_records, diffs)
            },
        }

    result = {
        "schema_version": "1.0",
        "protocol": "k=8 external graph-domain holdout, fully split solver matrix",
        "k": K,
        "iterations": 25,
        "training_seeds": list(TRAINING_SEEDS),
        "external_seeds": list(EXTERNAL_SEEDS),
        "external_graphs": 2,
        "candidate_strategies": list(STRATEGIES),
        "routers": routers,
        "majority_control": {
            "strategy": majority_strategy,
            "graphs": len(majority_values),
            "mean_relative_regret": sum(majority_values) / len(majority_values),
            "bootstrap_95_ci": [m_low, m_high],
            "graph_values": {
                record["dataset"]: value
                for record, value in zip(graph_records, majority_values)
            },
        },
        "paired_vs_majority": paired,
        "per_graph_results": graph_records,
        "unit_runtimes_seconds": unit_runtime,
        "evidence_boundary": [
            "The two graphs are external to the original 20-graph training corpus.",
            "The five external solver seeds are frozen and disjoint from prior k=8 routing seeds.",
            "All eight candidate strategies use the existing k=8 implementations and 25 iterations.",
            "Training topology labels and routing representations are frozen before external evaluation.",
            "This workflow changes execution granularity only; it does not change ATOF defaults.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "majority": result["majority_control"],
        "routers": result["routers"],
        "paired_vs_majority": result["paired_vs_majority"],
    }, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--training-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--topology-dir", type=Path, required=True)
    args = parser.parse_args()
    aggregate(args.input_dir, args.training_fixture, args.output, args.topology_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
