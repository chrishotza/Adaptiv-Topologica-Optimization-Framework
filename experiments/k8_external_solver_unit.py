from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path

import networkx as nx

from atof.native_backends import run_kaminpar, run_mtkahypar
from atof.portfolio import _edge_cut, _run_bloc, _run_kahip, _run_metis
from experiments.k8_degree_hub_replication import (
    _integer_feasible_imbalance,
    _pad_isolated_nodes,
    _postprocess_partition,
    _strip_padding,
)

K = 8
ITERATIONS = 25
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

DATASETS = {
    "ca_astroph": {
        "download_url": "https://snap.stanford.edu/data/ca-AstroPh.txt.gz",
        "directed": False,
    },
    "ca_condmat": {
        "download_url": "https://snap.stanford.edu/data/ca-CondMat.txt.gz",
        "directed": False,
    },
}


def load_graph(dataset: str, cache_dir: Path) -> tuple[nx.Graph, dict]:
    spec = DATASETS[dataset]
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = spec["download_url"].rsplit("/", 1)[-1]
    destination = cache_dir / filename
    if destination.exists():
        payload = destination.read_bytes()
        cache_hit = True
    else:
        request = urllib.request.Request(
            spec["download_url"],
            headers={"User-Agent": "ATOF/0.6.0"},
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

    provenance = {
        "download_url": spec["download_url"],
        "cache_hit": cache_hit,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "normalized_for_atof": "simple undirected graph with self-loops removed",
    }
    return graph, provenance


def run_one(graph: nx.Graph, strategy: str, seed: int) -> dict:
    started = time.perf_counter()
    retries = {}

    try:
        if strategy == "bloc":
            _, edge_cut, balance_error = _run_bloc(
                graph, seed=seed, iterations=ITERATIONS, variant="baseline", k=K
            )
        elif strategy == "bloc-affinity":
            _, edge_cut, balance_error = _run_bloc(
                graph, seed=seed, iterations=ITERATIONS, variant="affinity", k=K
            )
        elif strategy == "metis":
            try:
                partition, edge_cut, balance_error = _run_metis(
                    graph, seed=seed, k=K
                )
            except Exception as first_exc:
                padded_graph, padding_nodes = _pad_isolated_nodes(graph, K)
                imbalance = _integer_feasible_imbalance(padded_graph, K)
                partition, _, _ = _run_metis(
                    padded_graph,
                    seed=seed,
                    k=K,
                    recursive=False,
                    ufactor=int(__import__("math").ceil(imbalance * 1000)),
                )
                partition = _strip_padding(graph, partition, padding_nodes)
                partition, edge_cut, balance_error = _postprocess_partition(
                    graph, partition
                )
                retries["initial_error"] = f"{type(first_exc).__name__}: {first_exc}"
                retries["mode"] = "isolated_node_padding"
                retries["imbalance"] = imbalance
        elif strategy == "kahip":
            try:
                partition, edge_cut, balance_error = _run_kahip(
                    graph, seed=seed, k=K
                )
            except Exception as first_exc:
                padded_graph, padding_nodes = _pad_isolated_nodes(graph, K)
                imbalance = _integer_feasible_imbalance(padded_graph, K)
                partition, _, _ = _run_kahip(
                    padded_graph,
                    seed=seed,
                    k=K,
                    imbalance=imbalance,
                )
                partition = _strip_padding(graph, partition, padding_nodes)
                partition, edge_cut, balance_error = _postprocess_partition(
                    graph, partition
                )
                retries["initial_error"] = f"{type(first_exc).__name__}: {first_exc}"
                retries["mode"] = "feasible_imbalance_retry"
                retries["imbalance"] = imbalance
        elif strategy == "kaminpar":
            _, edge_cut, balance_error = run_kaminpar(
                graph, seed=seed, k=K, quality=False
            )
        elif strategy == "kaminpar-strong":
            _, edge_cut, balance_error = run_kaminpar(
                graph, seed=seed, k=K, quality=True
            )
        elif strategy == "mtkahypar":
            _, edge_cut, balance_error = run_mtkahypar(
                graph, seed=seed, k=K, quality=False
            )
        elif strategy == "mtkahypar-quality":
            _, edge_cut, balance_error = run_mtkahypar(
                graph, seed=seed, k=K, quality=True
            )
        else:
            raise ValueError(f"unknown strategy: {strategy}")

        return {
            "strategy": strategy,
            "seed": seed,
            "edge_cut": int(edge_cut),
            "balance_error": float(balance_error),
            "runtime_seconds": time.perf_counter() - started,
            "retries": retries,
            "error": None,
        }
    except Exception as exc:
        return {
            "strategy": strategy,
            "seed": seed,
            "edge_cut": None,
            "balance_error": None,
            "runtime_seconds": time.perf_counter() - started,
            "retries": retries,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    parser.add_argument("--strategy", choices=STRATEGIES, required=True)
    parser.add_argument("--seed", type=int, choices=EXTERNAL_SEEDS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()

    graph, provenance = load_graph(args.dataset, args.cache_dir)
    result = run_one(graph, args.strategy, args.seed)
    payload = {
        "schema_version": "1.0",
        "protocol": "k=8 external solver matrix unit",
        "dataset": args.dataset,
        "strategy": args.strategy,
        "seed": args.seed,
        "k": K,
        "iterations": ITERATIONS,
        "provenance": provenance,
        "result": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
