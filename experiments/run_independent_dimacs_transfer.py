from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_scaling_ablation import _run_config


EXPECTED_TOTAL_GRAPHS = 26
EXPECTED_CORPORA = {
    "development",
    "external",
    "snap",
    "snap_scalability",
    "dimacs",
}
EXPECTED_COUNTS = {
    "development": 7,
    "external": 4,
    "snap": 6,
    "snap_scalability": 3,
    "dimacs": 6,
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


def _load_blocks(block_dir: str | Path) -> dict[str, dict]:
    root = Path(block_dir)
    files = sorted(root.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no benchmark blocks found in {root}")

    blocks: dict[str, dict] = {}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        block = payload["block"]
        if block in blocks:
            raise AssertionError(f"duplicate benchmark block: {block}")
        blocks[block] = payload
    return blocks


def _assemble_records(blocks: dict[str, dict]):
    records: dict[str, dict[str, dict]] = {}
    provenance: dict[str, dict[str, dict]] = {}

    signatures = set()
    for block_name, payload in blocks.items():
        signature = json.dumps(
            payload["protocol_signature"],
            sort_keys=True,
            separators=(",", ":"),
        )
        signatures.add(signature)

        corpus = payload["corpus"]
        records.setdefault(corpus, {})
        provenance.setdefault(corpus, {})

        for graph_name, record in payload["records"].items():
            if graph_name in records[corpus]:
                raise AssertionError(
                    f"duplicate graph record {corpus}/{graph_name}"
                )
            records[corpus][graph_name] = record
            provenance[corpus][graph_name] = payload["provenance"][graph_name]

    if len(signatures) != 1:
        raise AssertionError("benchmark blocks have incompatible protocol signatures")

    return records, provenance, json.loads(next(iter(signatures)))


def aggregate_blocks(
    block_dir: str | Path,
    output_path: str | Path = (
        "results/generalization/independent_dimacs_transfer.json"
    ),
) -> dict:
    started = time.perf_counter()
    blocks = _load_blocks(block_dir)

    records, provenance, signature = _assemble_records(blocks)
    if set(records) != EXPECTED_CORPORA:
        raise AssertionError(
            f"unexpected corpora: {sorted(records)}"
        )

    observed_counts = {corpus: len(graphs) for corpus, graphs in records.items()}
    if observed_counts != EXPECTED_COUNTS:
        raise AssertionError(
            f"unexpected corpus graph counts: {observed_counts!r}; "
            f"expected {EXPECTED_COUNTS!r}"
        )

    total_graphs = sum(observed_counts.values())
    if total_graphs != EXPECTED_TOTAL_GRAPHS:
        raise AssertionError(
            f"expected {EXPECTED_TOTAL_GRAPHS} graphs, got {total_graphs}"
        )

    strategies = signature["candidate_strategies"]
    if signature["candidate_strategy_count"] != 9:
        raise AssertionError(
            f"expected 9 strategies, got {signature['candidate_strategy_count']}"
        )

    for record in [
        record for graphs in records.values() for record in graphs.values()
    ]:
        if sorted(record["strategy_means"]) != sorted(strategies):
            raise AssertionError("inconsistent strategy set across graph blocks")

    configs = {
        name: _run_config(records, *config)
        for name, config in LOCKED_CONFIGS.items()
    }

    oracle_distribution = {
        corpus: dict(
            Counter(record["oracle_strategy"] for record in graphs.values())
        )
        for corpus, graphs in records.items()
    }
    dimacs_oracle = dict(
        Counter(record["oracle_strategy"] for record in records["dimacs"].values())
    )

    payload = {
        "schema_version": "2.0",
        "protocol": (
            "five-corpus leave-one-corpus-out transfer assembled from reusable "
            "graph-local benchmark blocks"
        ),
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "total_graphs": total_graphs,
        "candidate_strategy_count": signature["candidate_strategy_count"],
        "candidate_strategies": strategies,
        "k": signature["k"],
        "seeds": signature["seeds"],
        "iterations": signature["iterations"],
        "blocks": {
            name: {
                "corpus": block["corpus"],
                "graphs": block["graph_names"],
                "graph_count": block["graph_count"],
                "block_commit_sha": block.get("commit_sha"),
                "runtime_seconds": block.get("runtime_seconds"),
            }
            for name, block in blocks.items()
        },
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in records.items()
        },
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
            "Graph-local partitioning and topology profiling are executed once per benchmark block.",
            "Downstream router analyses consume frozen block JSON and never recompute graph strategies or topology profiles.",
            "The candidate strategy set remains exactly the nine-strategy METIS+KaHIP-expanded set.",
            "The three locked routing configurations remain unchanged.",
            "Seeds remain 42, 101, and 2024; k=2; BLOC-RELOC refinement iterations remain 25.",
            "The DIMACS subset is prespecified by application diversity and availability, not by ATOF oracle outcome.",
            "The SNAP scalability corpus remains a distinct fourth fold and DIMACS is the fifth fold.",
            "For each held-out corpus, oracle labels and majority controls are learned only from the other four corpora.",
            "No feature, scaler, metric, or router hyperparameter is tuned during aggregation.",
        ],
        "reusability": (
            "The block JSON files are reusable benchmark state. Future routing, "
            "statistical, and sensitivity analyses should consume the blocks directly."
        ),
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = aggregate_blocks(args.blocks_dir, args.output)
    print(
        json.dumps(
            {
                name: value["macro"]
                for name, value in result["configs"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
