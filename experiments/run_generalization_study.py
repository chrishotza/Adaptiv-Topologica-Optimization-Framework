from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx

from atof.generalization import summarize_generalization
from experiments.run_external_validation import run_external_validation
from experiments.run_routing_evaluation import run_routing_evaluation
from experiments.run_snap_validation import run_snap_validation


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _routing_folds(payload: dict) -> list[dict]:
    """Extract graph-level routing folds from a validation payload."""
    routing = payload.get("routing")
    if routing is not None:
        return list(routing.get("folds", []))
    return list(payload.get("folds", []))


def combine_routing_payloads(corpora: dict[str, dict]) -> dict:
    """Build a descriptive cross-corpus manifest from routing payloads."""
    folds = {
        name: _routing_folds(payload)
        for name, payload in corpora.items()
    }
    summary = summarize_generalization(folds)

    return {
        "schema_version": "0.1",
        "protocol": "cross-corpus graph-level routing generalization",
        "unit_of_analysis": "held-out graph",
        "corpora": {
            name: {
                "graphs": summary["corpora"][name]["graphs"],
                "routing_protocol": payload.get(
                    "routing", {}
                ).get(
                    "protocol",
                    payload.get("protocol", "unknown"),
                ),
            }
            for name, payload in corpora.items()
        },
        "summary": summary,
    }


def run_generalization_study(
    output_path: str | Path = "results/generalization/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    bootstrap_resamples: int = 5000,
    cache_dir: str | Path | None = None,
) -> dict:
    """Run the aligned development + external + routine SNAP study."""
    if k != 2:
        raise ValueError("The aligned generalization study currently requires k=2.")

    started = time.perf_counter()

    development = run_routing_evaluation(
        output_path=Path(output_path).with_name("routing_development.json"),
        k=k,
        seeds=seeds,
        iterations=iterations,
    )
    external = run_external_validation(
        output_path=Path(output_path).with_name("routing_external.json"),
        k=k,
        seeds=seeds,
        iterations=iterations,
        bootstrap_resamples=bootstrap_resamples,
    )
    snap = run_snap_validation(
        output_path=Path(output_path).with_name("routing_snap.json"),
        k=k,
        seeds=seeds,
        iterations=iterations,
        bootstrap_resamples=bootstrap_resamples,
        cache_dir=cache_dir,
    )

    payload = combine_routing_payloads(
        {
            "development": development,
            "external": external,
            "snap": snap,
        }
    )
    payload.update(
        {
            "created_at": time.time(),
            "python": sys.version,
            "platform": platform.platform(),
            "networkx": nx.__version__,
            "commit_sha": _commit_sha(),
            "k": k,
            "seeds": list(seeds),
            "iterations": iterations,
            "bootstrap_resamples": bootstrap_resamples,
            "notes": [
                "Development, external, and SNAP corpora are summarized independently before cross-corpus aggregation.",
                "Repeated seeds remain nested within graphs; the held-out graph is the routing unit.",
                "SNAP source files are downloaded live when absent from the configured cache and their SHA-256 values are preserved in routing_snap.json.",
                "This manifest is descriptive infrastructure and is not a claim of universal routing generalization.",
            ],
            "runtime_seconds": time.perf_counter() - started,
        }
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_generalization_study()
    print(
        json.dumps(
            {
                "corpus_count": result["summary"]["corpus_count"],
                "graph_count": result["summary"]["graph_count"],
                "micro": result["summary"]["micro"],
                "macro": result["summary"]["macro"],
            },
            indent=2,
        )
    )
