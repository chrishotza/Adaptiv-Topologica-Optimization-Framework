from __future__ import annotations

import argparse
import gzip
import io
import json
import platform
import subprocess
import time
import urllib.request
from pathlib import Path

import networkx as nx

from atof.portfolio import optimize_portfolio
from atof.routing import FEATURE_GROUPS
from atof.topology import TopologyProfiler

SEED = 5003
K = 8
GRAPH = {
    "name": "ego_facebook",
    "download_url": "https://snap.stanford.edu/data/facebook_combined.txt.gz",
    "reference_url": "https://snap.stanford.edu/data/ego-Facebook.html",
    "directed": False,
    "declared_nodes": 4039,
    "declared_edges": 88234,
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


def _load_graph(cache_dir: Path) -> tuple[nx.Graph, dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / "facebook_combined.txt.gz"
    started = time.perf_counter()
    if destination.exists():
        payload = destination.read_bytes()
        cache_hit = True
    else:
        request = urllib.request.Request(
            GRAPH["download_url"],
            headers={"User-Agent": "ATOF/0.6.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        destination.write_bytes(payload)
        cache_hit = False
    download_seconds = time.perf_counter() - started

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
    graph = nx.convert_node_labels_to_integers(graph, ordering="default")
    return graph, {
        "cache_hit": cache_hit,
        "download_seconds": download_seconds,
        "bytes": len(payload),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }


def _profile(graph: nx.Graph, features=None) -> dict:
    profiler = TopologyProfiler(features=features)
    started = time.perf_counter()
    profile = profiler.profile(graph).to_dict()
    elapsed = time.perf_counter() - started
    return {
        "seconds": elapsed,
        "features_requested": list(profiler.features),
        "profile": {
            key: value
            for key, value in profile.items()
            if key in profiler.features
        },
    }


def run(output_path: str | Path, cache_dir: str | Path) -> dict:
    started = time.perf_counter()
    graph, load_info = _load_graph(Path(cache_dir))

    full_profile = _profile(graph)
    global_profile = _profile(
        graph,
        features=FEATURE_GROUPS["global_paths"],
    )
    degree_hub_profile = _profile(
        graph,
        features=FEATURE_GROUPS["degree_hub"],
    )

    solver_started = time.perf_counter()
    result = optimize_portfolio(
        graph,
        k=K,
        seed=SEED,
        iterations=25,
        include_optional=True,
    )
    solver_seconds = time.perf_counter() - solver_started

    candidates = {
        candidate.id: {
            "available": candidate.available,
            "runtime_seconds": candidate.runtime_seconds,
            "edge_cut": candidate.edge_cut,
            "balance_error": candidate.balance_error,
            "error": candidate.error,
        }
        for candidate in result.candidates
    }

    payload = {
        "schema_version": "1.0",
        "protocol": "k=8 external runtime preflight",
        "commit_sha": _commit_sha(),
        "platform": platform.platform(),
        "k": K,
        "seed": SEED,
        "graph": {
            **GRAPH,
            **load_info,
        },
        "profile_timing": {
            "all": full_profile,
            "global_paths": global_profile,
            "degree_hub": degree_hub_profile,
        },
        "solver": {
            "total_seconds": solver_seconds,
            "candidates": candidates,
        },
        "runtime_seconds_total": time.perf_counter() - started,
        "decision_rule": [
            "This is a feasibility/timing probe only.",
            "It does not produce routing evidence and must not be used as a performance result.",
            "The full external holdout will not be relaunched from this probe automatically.",
        ],
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "graph_nodes": load_info["nodes"],
                "graph_edges": load_info["edges"],
                "profile_all_seconds": full_profile["seconds"],
                "profile_global_paths_seconds": global_profile["seconds"],
                "profile_degree_hub_seconds": degree_hub_profile["seconds"],
                "solver_total_seconds": solver_seconds,
                "candidate_runtimes": {
                    key: value["runtime_seconds"]
                    for key, value in candidates.items()
                },
                "total_seconds": payload["runtime_seconds_total"],
            },
            indent=2,
        )
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
