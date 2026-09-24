from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from atof.portfolio import optimize_portfolio
from atof.snap import download_snap_dataset, snap_scalability_corpus


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_snap_kway_scalability(
    output_path: str | Path = "results/snap/kway-scalability-latest.json",
    *,
    cache_dir: str | Path | None = None,
    ks: tuple[int, ...] = (2, 4, 8),
    seed: int = 42,
    iterations: int = 5,
    include_optional: bool = True,
) -> dict:
    """Stress the Portfolio k-way contract on the larger SNAP corpus."""
    started = time.perf_counter()
    rows: list[dict] = []

    for dataset in snap_scalability_corpus():
        graph, provenance = download_snap_dataset(dataset, cache_dir=cache_dir)
        for k in ks:
            if k > graph.number_of_nodes():
                rows.append({
                    "dataset": dataset.name,
                    "k": k,
                    "status": "skipped",
                    "error": "k exceeds graph node count",
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                })
                continue

            started_run = time.perf_counter()
            try:
                result = optimize_portfolio(
                    graph,
                    k=k,
                    seed=seed,
                    iterations=iterations,
                    include_optional=include_optional,
                    profile_mode="bounded",
                )
                rows.append({
                    "dataset": dataset.name,
                    "k": k,
                    "status": "ok",
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "selected_strategy": result.selected_strategy,
                    "selected_edge_cut": result.selected_edge_cut,
                    "selected_balance_error": result.selected_balance_error,
                    "runtime_seconds": time.perf_counter() - started_run,
                    "profile_mode": result.profile_mode,
                    "candidates": [candidate.to_dict() for candidate in result.candidates],
                })
            except Exception as exc:
                rows.append({
                    "dataset": dataset.name,
                    "k": k,
                    "status": "error",
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "runtime_seconds": time.perf_counter() - started_run,
                    "error": f"{type(exc).__name__}: {exc}",
                })

    payload = {
        "schema_version": "0.1",
        "protocol": "Portfolio k-way operational stress on the SNAP scalability corpus",
        "corpus_type": "snap_scalability",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "commit_sha": _commit_sha(),
        "parameters": {
            "ks": list(ks),
            "seed": seed,
            "iterations": iterations,
            "include_optional": include_optional,
            "profile_mode": "bounded",
        },
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "This is an operational stress test, not a quality-ranking benchmark.",
            "Observed runtime depends on installed optional backends and the CI machine.",
            "The SNAP corpus is an external stress surface, not a representative population sample.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_snap_kway_scalability()
    print(json.dumps({
        "rows": len(result["rows"]),
        "ok": sum(row["status"] == "ok" for row in result["rows"]),
        "errors": sum(row["status"] == "error" for row in result["rows"]),
    }, indent=2))
