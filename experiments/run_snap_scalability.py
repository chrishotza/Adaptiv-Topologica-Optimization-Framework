from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from atof.snap import download_snap_dataset, snap_scalability_corpus
from atof.topology import TopologyProfiler


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _safe_profile(profile) -> dict:
    return {
        key: (None if isinstance(value, float) and math.isnan(value) else value)
        for key, value in profile.to_dict().items()
    }


def run_snap_scalability(
    output_path: str | Path = "results/snap/scalability-latest.json",
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    """Measure bounded topology profiling on the larger SNAP corpus."""
    started = time.perf_counter()
    profiler = TopologyProfiler()
    rows: list[dict] = []

    for dataset in snap_scalability_corpus():
        load_started = time.perf_counter()
        graph, provenance = download_snap_dataset(dataset, cache_dir=cache_dir)
        load_seconds = time.perf_counter() - load_started

        profile_started = time.perf_counter()
        profile = profiler.profile(graph, mode="bounded")
        profile_seconds = time.perf_counter() - profile_started

        rows.append({
            "dataset": dataset.name,
            "declared_nodes": dataset.nodes,
            "declared_edges": dataset.edges,
            "loaded_nodes": graph.number_of_nodes(),
            "loaded_edges": graph.number_of_edges(),
            "load_seconds": load_seconds,
            "profile_seconds": profile_seconds,
            "profile_mode": "bounded",
            "profile": _safe_profile(profile),
            "expensive_path_metrics_skipped": (
                math.isnan(profile.diameter) or math.isnan(profile.avg_path_length)
            ),
            "modularity_skipped": math.isnan(profile.modularity),
            "provenance": provenance,
        })

    payload = {
        "schema_version": "0.1",
        "protocol": "bounded topology profiling on the SNAP scalability corpus",
        "corpus_type": "snap_scalability",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "commit_sha": _commit_sha(),
        "profiler_limits": {
            "mode": "bounded",
            "expensive_path_node_limit": 2000,
            "modularity_node_limit": 2000,
        },
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "This measurement evaluates the bounded product profiling path only.",
            "It does not establish runtime or memory bounds for the full exact profiler on the scalability corpus.",
            "The SNAP corpus is an external stress surface, not a representative population sample.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_snap_scalability()
    print(json.dumps({
        "datasets": len(result["rows"]),
        "profile_mode": result["profiler_limits"]["mode"],
        "runtime_seconds": result["runtime_seconds"],
    }, indent=2))
