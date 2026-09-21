from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from experiments.run_cross_corpus_transfer import _mean
from experiments.run_kahip_validation import STRATEGY as KAHIP_STRATEGY
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY
from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_kahip_confirmatory import (
    _benchmark_graph_with_kahip,
)
from experiments.run_router_scaling_ablation import _run_config
from atof.snap import download_snap_dataset, snap_scalability_corpus
from experiments.run_cross_corpus_transfer import _load_corpora


EXPECTED_STRATEGY_COUNT = 9
EXPECTED_TOTAL_GRAPHS = 20


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _load_expanded_corpora(*, cache_dir: str | Path | None = None):
    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    corpora["snap_scalability"] = {}
    provenance["snap_scalability"] = {}

    for dataset in snap_scalability_corpus():
        graph, metadata = download_snap_dataset(
            dataset,
            cache_dir=cache_dir,
        )
        corpora["snap_scalability"][dataset.name] = graph
        provenance["snap_scalability"][dataset.name] = metadata

    return corpora, provenance


def run_expanded_transfer(
    output_path: str | Path = (
        "results/generalization/expanded_20graph_kahip_transfer.json"
    ),
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError("The expanded transfer protocol requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)

    records = {
        corpus: {
            name: _benchmark_graph_with_kahip(
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

    first_record = next(
        record for graphs in records.values() for record in graphs.values()
    )
    strategies = set(first_record["strategy_means"])
    if len(strategies) != EXPECTED_STRATEGY_COUNT:
        raise AssertionError(
            f"expected 9 strategies, got {len(strategies)}"
        )
    if METIS_STRATEGY not in strategies:
        raise AssertionError("METIS missing from expanded candidate set")
    if KAHIP_STRATEGY not in strategies:
        raise AssertionError("KaHIP missing from expanded candidate set")

    total_graphs = sum(len(graphs) for graphs in records.values())
    if total_graphs != EXPECTED_TOTAL_GRAPHS:
        raise AssertionError(
            f"expected {EXPECTED_TOTAL_GRAPHS} graphs, got {total_graphs}"
        )

    configs = {
        name: _run_config(records, *config)
        for name, config in LOCKED_CONFIGS.items()
    }

    oracle_distribution = {
        corpus: dict(
            Counter(
                record["oracle_strategy"]
                for record in graphs.values()
            )
        )
        for corpus, graphs in records.items()
    }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "expanded four-corpus leave-one-corpus-out router transfer with "
            "nine partitioning strategies"
        ),
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "candidate_strategy_count": EXPECTED_STRATEGY_COUNT,
        "candidate_strategies": sorted(strategies),
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "total_graphs": total_graphs,
        "oracle_distribution": oracle_distribution,
        "locked_configs": {
            name: {
                "features": list(config[0]),
                "scale_mode": config[1],
                "metric": config[2],
            }
            for name, config in LOCKED_CONFIGS.items()
        },
        "configs": configs,
        "protocol_controls": [
            "The three locked router configurations are unchanged from the previous confirmatory experiments.",
            "The candidate strategy set remains exactly the nine-strategy METIS+KaHIP-expanded set.",
            "The added fourth corpus is the pre-existing SNAP scalability corpus in the repository: ca-GrQc, ca-HepTh, and wiki-Vote.",
            "For each held-out corpus, graph-level oracle labels are learned only from the other three corpora.",
            "The majority control remains mandatory and is recomputed per held-out corpus.",
            "No feature, scaler, metric, or router hyperparameter is tuned on this run.",
            "This is corpus-expansion evidence; it does not change the public/default router.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_expanded_transfer()
    print(
        json.dumps(
            {
                name: value["macro"]
                for name, value in result["configs"].items()
            },
            indent=2,
        )
    )
