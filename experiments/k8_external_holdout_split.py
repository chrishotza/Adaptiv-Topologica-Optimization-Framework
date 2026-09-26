from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import platform
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

import networkx as nx

from atof.routing import FEATURE_GROUPS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from experiments.k8_degree_hub_replication import _graph_record

K = 8
TRAINING_SEEDS = (42, 101, 2024)
EXTERNAL_SEEDS = (5003, 7003, 9001, 12011, 16001)
RESAMPLES = 5000
BOOTSTRAP_SEED = 2024

ROUTER_CONFIGS = {
    "all_iqr_l2": tuple(FEATURE_GROUPS["all"]),
    "global_paths_iqr_l2": tuple(FEATURE_GROUPS["global_paths"]),
}

EXTERNAL_DATASETS = {
    "ego_facebook": {
        "source": "McAuley & Leskovec (2012), SNAP",
        "reference_url": "https://snap.stanford.edu/data/ego-Facebook.html",
        "download_url": "https://snap.stanford.edu/data/facebook_combined.txt.gz",
        "directed": False,
        "declared_nodes": 4039,
        "declared_edges": 88234,
    },
    "p2p_gnutella08": {
        "source": "Ripeanu, Foster & Iamnitchi; SNAP",
        "reference_url": "https://snap.stanford.edu/data/p2p-Gnutella08.html",
        "download_url": "https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz",
        "directed": True,
        "declared_nodes": 6301,
        "declared_edges": 20777,
    },
    "ca_astroph": {
        "source": "SNAP Arxiv Astro Physics collaboration network",
        "reference_url": "https://snap.stanford.edu/data/ca-AstroPh.html",
        "download_url": "https://snap.stanford.edu/data/ca-AstroPh.txt.gz",
        "directed": False,
        "declared_nodes": 18772,
        "declared_edges": 198110,
    },
    "ca_condmat": {
        "source": "SNAP Arxiv Condensed Matter collaboration network",
        "reference_url": "https://snap.stanford.edu/data/ca-CondMat.html",
        "download_url": "https://snap.stanford.edu/data/ca-CondMat.txt.gz",
        "directed": False,
        "declared_nodes": 23133,
        "declared_edges": 93497,
    },
}

def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def _make_fixture(source_path: Path, output_path: Path) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    strategies = list(source["candidate_strategies"])
    records = []
    for item in source["graph_manifest"]:
        by_seed = item["by_seed"]
        strategy_means = {
            strategy: sum(
                float(by_seed[str(seed)][strategy]["edge_cut"])
                for seed in TRAINING_SEEDS
            ) / len(TRAINING_SEEDS)
            for strategy in strategies
        }
        oracle = min(strategy_means, key=lambda name: (strategy_means[name], name))
        records.append(
            {
                "corpus": item["corpus"],
                "graph": item["graph"],
                "graph_id": item["graph_id"],
                "topology": item["topology"],
                "strategy_means": strategy_means,
                "oracle_strategy": oracle,
                "training_seeds": list(TRAINING_SEEDS),
            }
        )
    if len(records) != 20:
        raise AssertionError(f"expected 20 training graphs, got {len(records)}")
    result = {
        "schema_version": "1.0",
        "protocol": "frozen k=8 training fixture reconstructed from prior five-seed replication",
        "training_seeds": list(TRAINING_SEEDS),
        "candidate_strategies": strategies,
        "graphs": records,
        "source_artifact_sha256": "31b81196870aa9159c91e21bded78d9b472e04f7ab8d0fa28be07fdeec328726",
        "source_commit": source.get("commit_sha"),
        "evidence_note": (
            "Only seeds 42, 101, 2024 are reconstructed into training means; "
            "no external holdout outcome is used."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def _load_graph(spec: dict, cache_dir: Path) -> tuple[nx.Graph, dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = spec["download_url"].rsplit("/", 1)[-1]
    destination = cache_dir / filename
    if destination.exists():
        payload = destination.read_bytes()
        cache_hit = True
    else:
        request = urllib.request.Request(
            spec["download_url"], headers={"User-Agent": "ATOF/0.6.0"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        destination.write_bytes(payload)
        cache_hit = False
    graph = nx.Graph()
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        for raw in io.TextIOWrapper(stream, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                graph.add_edge(parts[0], parts[1])
    if spec["directed"]:
        graph = graph.to_undirected()
    graph.remove_edges_from(nx.selfloop_edges(graph))
    graph = nx.convert_node_labels_to_integers(graph, ordering="default")
    metadata = {
        "source": spec["source"],
        "reference_url": spec["reference_url"],
        "download_url": spec["download_url"],
        "cache_path": str(destination),
        "cache_hit": cache_hit,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "declared_nodes": spec["declared_nodes"],
        "declared_edges": spec["declared_edges"],
        "loaded_nodes": graph.number_of_nodes(),
        "loaded_edges": graph.number_of_edges(),
        "directed_source": spec["directed"],
        "normalized_for_atof": "simple undirected graph with self-loops removed",
    }
    return graph, metadata

def _load_training(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["training_seeds"] != list(TRAINING_SEEDS):
        raise AssertionError("training seed grid mismatch")
    if len(data["graphs"]) != 20:
        raise AssertionError("training fixture must contain 20 graphs")
    return data["graphs"]

def _fit(training_records: list[dict], features: tuple[str, ...]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in training_records
    ]
    return LearnedTopologyRouter(
        features=features,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)

def _regret(record: dict, selected: str) -> float:
    oracle_cut = float(record["strategy_means"][record["oracle_strategy"]])
    selected_cut = float(record["strategy_means"][selected])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0

def _external(dataset: str, training_fixture: Path, output_path: Path, cache_dir: Path) -> dict:
    started = time.perf_counter()
    if dataset not in EXTERNAL_DATASETS:
        raise ValueError(f"unknown dataset: {dataset}")
    training = _load_training(training_fixture)
    graph, provenance = _load_graph(EXTERNAL_DATASETS[dataset], cache_dir)
    record = _graph_record(
        graph,
        "external_holdout",
        dataset,
        seeds=EXTERNAL_SEEDS,
    )
    if len(record["seed_oracles"]) != len(EXTERNAL_SEEDS):
        raise AssertionError("external seed grid incomplete")
    routers = {}
    for name, features in ROUTER_CONFIGS.items():
        router = _fit(training, features)
        selected = router.predict(record["topology"])
        routers[name] = {
            "selected_strategy": selected,
            "relative_regret": _regret(record, selected),
        }
    oracle_counts = Counter(item["oracle_strategy"] for item in training)
    majority_strategy = min(
        oracle_counts,
        key=lambda strategy: (-oracle_counts[strategy], strategy),
    )
    majority_regret = _regret(record, majority_strategy)
    result = {
        "schema_version": "1.0",
        "protocol": "k=8 external graph holdout split job",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": K,
        "dataset": dataset,
        "training_seeds": list(TRAINING_SEEDS),
        "external_seeds": list(EXTERNAL_SEEDS),
        "training_graphs": len(training),
        "candidate_strategies": list(record["strategy_means"]),
        "provenance": provenance,
        "routers": routers,
        "majority_strategy": majority_strategy,
        "majority_relative_regret": majority_regret,
        "record": record,
        "runtime_seconds": time.perf_counter() - started,
        "evidence_boundary": [
            "Training data are reconstructed only from prior frozen results for seeds 42, 101, 2024.",
            "The external graph and external seed outcomes are generated in this job only.",
            "No external outcome is used to fit the routers.",
            "All routing configurations are frozen before external outcomes are evaluated.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "dataset": dataset,
        "all_iqr_l2": routers["all_iqr_l2"],
        "global_paths_iqr_l2": routers["global_paths_iqr_l2"],
        "majority_strategy": majority_strategy,
        "majority_relative_regret": majority_regret,
        "runtime_seconds": result["runtime_seconds"],
    }, indent=2))
    return result

def _aggregate(input_dir: Path, output_path: Path) -> dict:
    files = sorted(input_dir.glob("*.json"))
    if len(files) != 4:
        raise AssertionError(f"expected 4 external result files, got {len(files)}")
    results = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    datasets = [item["dataset"] for item in results]
    if len(set(datasets)) != 4:
        raise AssertionError("external datasets are not unique")
    all_results = {}
    for router_name in ROUTER_CONFIGS:
        values = [float(item["routers"][router_name]["relative_regret"]) for item in results]
        low, high = bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
        all_results[router_name] = {
            "graphs": len(values),
            "mean_relative_regret": _mean(values),
            "bootstrap_95_ci": [low, high],
            "graph_values": dict(zip(datasets, values)),
        }
    majority_values = [float(item["majority_relative_regret"]) for item in results]
    m_low, m_high = bootstrap_mean_ci(
        majority_values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED
    )
    majority = {
        "strategy": results[0]["majority_strategy"],
        "graphs": len(majority_values),
        "mean_relative_regret": _mean(majority_values),
        "bootstrap_95_ci": [m_low, m_high],
        "graph_values": dict(zip(datasets, majority_values)),
    }
    paired = {}
    for router_name in ROUTER_CONFIGS:
        values = [
            float(item["routers"][router_name]["relative_regret"])
            - float(item["majority_relative_regret"])
            for item in results
        ]
        low, high = bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
        paired[router_name] = {
            "mean_router_minus_majority": _mean(values),
            "bootstrap_95_ci": [low, high],
            "router_better_graphs": sum(value < 0 for value in values),
            "router_worse_graphs": sum(value > 0 for value in values),
            "ties": sum(value == 0 for value in values),
            "graph_values": dict(zip(datasets, values)),
        }
    output = {
        "schema_version": "1.0",
        "protocol": "k=8 external graph-domain holdout, split execution",
        "commit_sha": _commit_sha(),
        "k": K,
        "training_seeds": list(TRAINING_SEEDS),
        "external_seeds": list(EXTERNAL_SEEDS),
        "external_graphs": 4,
        "datasets": datasets,
        "routers": all_results,
        "majority_control": majority,
        "paired_vs_majority": paired,
        "per_graph_results": results,
        "evidence_boundary": [
            "Four external SNAP graphs are outside the original 20-graph training corpus.",
            "External solver seeds are 5003, 7003, 9001, 12011, 16001.",
            "The training representation and scaling are frozen before external scoring.",
            "This split workflow does not modify production/default routing behavior.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"majority": majority, "routers": all_results, "paired_vs_majority": paired}, indent=2))
    return output

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    fixture = sub.add_parser("make-fixture")
    fixture.add_argument("--source", type=Path, required=True)
    fixture.add_argument("--output", type=Path, required=True)
    external = sub.add_parser("external")
    external.add_argument("--dataset", required=True, choices=sorted(EXTERNAL_DATASETS))
    external.add_argument("--training-fixture", type=Path, required=True)
    external.add_argument("--output", type=Path, required=True)
    external.add_argument("--cache-dir", type=Path, required=True)
    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--input-dir", type=Path, required=True)
    aggregate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "make-fixture":
        _make_fixture(args.source, args.output)
    elif args.mode == "external":
        _external(args.dataset, args.training_fixture, args.output, args.cache_dir)
    else:
        _aggregate(args.input_dir, args.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
