from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx

from atof.datasets import standard_reference_corpus
from atof.dimacs import download_dimacs_dataset, dimacs_independent_corpus
from atof.snap import (
    download_snap_dataset,
    snap_reference_corpus,
    snap_scalability_corpus,
)
from experiments.generate_suite import build_suite
from experiments.run_kahip_validation import STRATEGY as KAHIP_STRATEGY
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY
from experiments.run_router_kahip_confirmatory import _benchmark_graph_with_kahip


EXPECTED_STRATEGIES = 9
SEEDS = (42, 101, 2024)
ITERATIONS = 25
K = 2

BLOCKS: dict[str, tuple[str, tuple[str, ...]]] = {
    "development": ("development", tuple(build_suite().keys())),
    "external": ("external", tuple(item.name for item in standard_reference_corpus())),
    "snap": ("snap", tuple(item.name for item in snap_reference_corpus())),
    "snap_scalability_ca_grqc": ("snap_scalability", ("ca_grqc",)),
    "snap_scalability_ca_hepth": ("snap_scalability", ("ca_hepth",)),
    "snap_scalability_wiki_vote": ("snap_scalability", ("wiki_vote",)),
    "dimacs_jazz": ("dimacs", ("jazz",)),
    "dimacs_email_urv": ("dimacs", ("email_urv",)),
    "dimacs_pgp_giant": ("dimacs", ("pgp_giant",)),
    "dimacs_as_22july06": ("dimacs", ("as_22july06",)),
    "dimacs_power": ("dimacs", ("power",)),
    "dimacs_astro_ph": ("dimacs", ("astro_ph",)),
}


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _load_graphs(
    corpus: str,
    names: tuple[str, ...],
    *,
    cache_dir: str | Path | None,
) -> tuple[dict[str, nx.Graph], dict[str, dict]]:
    provenance: dict[str, dict] = {}

    if corpus == "development":
        source = dict(build_suite())
        return (
            {name: source[name] for name in names},
            {name: {"type": "deterministic_networkx_synthetic"} for name in names},
        )

    if corpus == "external":
        datasets = {item.name: item for item in standard_reference_corpus()}
        graphs = {}
        for name in names:
            dataset = datasets[name]
            graph = dataset.load()
            graphs[name] = graph
            provenance[name] = {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "source": dataset.source,
                "reference_url": dataset.reference_url,
                "notes": dataset.notes,
            }
        return graphs, provenance

    if corpus == "snap":
        datasets = {item.name: item for item in snap_reference_corpus()}
    elif corpus == "snap_scalability":
        datasets = {item.name: item for item in snap_scalability_corpus()}
    elif corpus == "dimacs":
        datasets = {item.name: item for item in dimacs_independent_corpus()}
    else:
        raise ValueError(f"unknown corpus: {corpus}")

    graphs = {}
    for name in names:
        dataset = datasets[name]
        if corpus == "dimacs":
            graph, metadata = download_dimacs_dataset(dataset, cache_dir=cache_dir)
        else:
            graph, metadata = download_snap_dataset(dataset, cache_dir=cache_dir)
        graphs[name] = graph
        provenance[name] = metadata
    return graphs, provenance


def run_block(
    block: str,
    output_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    if block not in BLOCKS:
        raise ValueError(f"unknown block {block!r}; valid blocks: {sorted(BLOCKS)}")

    corpus, names = BLOCKS[block]
    started = time.perf_counter()
    graphs, provenance = _load_graphs(corpus, names, cache_dir=cache_dir)

    records = {}
    for name, graph in graphs.items():
        records[name] = _benchmark_graph_with_kahip(
            graph,
            corpus=corpus,
            name=name,
            seeds=SEEDS,
            iterations=ITERATIONS,
        )

    first = next(iter(records.values()))
    strategies = sorted(first["strategy_means"])
    if len(strategies) != EXPECTED_STRATEGIES:
        raise AssertionError(f"expected {EXPECTED_STRATEGIES} strategies, got {len(strategies)}")
    if METIS_STRATEGY not in strategies:
        raise AssertionError("METIS missing from block result")
    if KAHIP_STRATEGY not in strategies:
        raise AssertionError("KaHIP missing from block result")

    payload = {
        "schema_version": "2.0",
        "block": block,
        "corpus": corpus,
        "graph_names": list(names),
        "graph_count": len(records),
        "protocol_signature": {
            "k": K,
            "seeds": list(SEEDS),
            "iterations": ITERATIONS,
            "candidate_strategy_count": EXPECTED_STRATEGIES,
            "candidate_strategies": strategies,
        },
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "provenance": provenance,
        "records": records,
        "runtime_seconds": time.perf_counter() - started,
        "reusability": (
            "This block is graph-local benchmark state. Downstream router analyses "
            "must consume this JSON without rerunning partitioning or topology profiling."
        ),
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", required=True, choices=sorted(BLOCKS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--cache-dir", default=None)
    args = parser.parse_args()
    result = run_block(
        args.block,
        args.output,
        cache_dir=args.cache_dir,
    )
    print(
        json.dumps(
            {
                "block": result["block"],
                "corpus": result["corpus"],
                "graphs": result["graph_count"],
                "runtime_seconds": result["runtime_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
