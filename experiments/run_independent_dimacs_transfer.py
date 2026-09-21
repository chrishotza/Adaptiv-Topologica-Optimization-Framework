from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from atof.dimacs import download_dimacs_dataset, dimacs_independent_corpus
from experiments.run_cross_corpus_transfer import _load_corpora
from experiments.run_kahip_validation import STRATEGY as KAHIP_STRATEGY
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY
from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_kahip_confirmatory import _benchmark_graph_with_kahip
from experiments.run_router_scaling_ablation import _run_config


EXPECTED_STRATEGY_COUNT = 9
EXPECTED_TOTAL_GRAPHS = 26
EXPECTED_CORPORA = {
    "development",
    "external",
    "snap",
    "snap_scalability",
    "dimacs",
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


def _load_independent_corpora(*, cache_dir: str | Path | None = None):
    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    corpora["dimacs"] = {}
    provenance["dimacs"] = {}

    for dataset in dimacs_independent_corpus():
        graph, metadata = download_dimacs_dataset(
            dataset,
            cache_dir=cache_dir,
        )
        corpora["dimacs"][dataset.name] = graph
        provenance["dimacs"][dataset.name] = metadata

    return corpora, provenance


def run_independent_transfer(
    output_path: str | Path = (
        "results/generalization/independent_dimacs_transfer.json"
    ),
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError("The independent DIMACS transfer protocol requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_independent_corpora(cache_dir=cache_dir)

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
        raise AssertionError("METIS missing from candidate set")
    if KAHIP_STRATEGY not in strategies:
        raise AssertionError("KaHIP missing from candidate set")

    total_graphs = sum(len(graphs) for graphs in records.values())
    if total_graphs != EXPECTED_TOTAL_GRAPHS:
        raise AssertionError(
            f"expected {EXPECTED_TOTAL_GRAPHS} graphs, got {total_graphs}"
        )
    if set(records) != EXPECTED_CORPORA:
        raise AssertionError(f"unexpected corpora: {sorted(records)}")

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

    independent = records["dimacs"]
    dimacs_oracle = dict(
        Counter(record["oracle_strategy"] for record in independent.values())
    )

    payload = {
        "schema_version": "1.0",
        "protocol": (
            "five-corpus leave-one-corpus-out transfer with a prespecified "
            "independent DIMACS clustering testbed"
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
        "dimacs_oracle_distribution": dimacs_oracle,
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
            "The candidate strategy set remains exactly the nine-strategy METIS+KaHIP-expanded set.",
            "The three locked routing configurations remain unchanged from the prior confirmatory protocol.",
            "Seeds remain 42, 101, and 2024; k=2; BLOC-RELOC refinement iterations remain 25.",
            "The DIMACS subset was prespecified by application diversity and availability from the 10th DIMACS clustering testbed; no graph was selected using its ATOF oracle outcome.",
            "The DIMACS corpus is held out as a complete fifth fold.",
            "For each held-out corpus, graph-level oracle labels are learned only from the other four corpora.",
            "The majority control is recomputed per held-out corpus.",
            "No feature, scaler, metric, or router hyperparameter is tuned on the independent run.",
            "This experiment is a validation of transfer and does not modify the public/default router.",
        ],
        "hypothesis": (
            "The strongest 20-graph scalability-fold signal should transfer to "
            "an independent real-world partitioning corpus when topology "
            "features identify graphs for which the fixed majority strategy "
            "is not the lowest-regret choice."
        ),
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_independent_transfer()
    print(
        json.dumps(
            {
                name: value["macro"]
                for name, value in result["configs"].items()
            },
            indent=2,
        )
    )
