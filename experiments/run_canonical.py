from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from atof.selector import HeuristicRegimeSelector
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler


def balanced_round_robin(graph: nx.Graph, k: int) -> dict:
    """Deterministic balanced baseline with no optimization."""
    partition = {node: i % k for i, node in enumerate(graph.nodes())}
    cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return {"edge_cut": int(cut), "balance_error": 0.0, "weighted_cost": float(cut)}


def random_balanced(graph: nx.Graph, k: int, seed: int) -> dict:
    """Random balanced assignment with deterministic seed."""
    rng = random.Random(seed)
    nodes = list(graph.nodes())
    rng.shuffle(nodes)
    partition = {node: i % k for i, node in enumerate(nodes)}
    cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return {"edge_cut": int(cut), "balance_error": 0.0, "weighted_cost": float(cut)}


def kernighan_lin(graph: nx.Graph, seed: int) -> dict:
    """NetworkX implementation of Kernighan-Lin for a 2-way partition."""
    a, b = nx.algorithms.community.kernighan_lin_bisection(
        graph, max_iter=10, seed=seed
    )
    partition = {node: 0 for node in a}
    partition.update({node: 1 for node in b})
    cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return {"edge_cut": int(cut), "balance_error": 0.0, "weighted_cost": float(cut)}


def _safe_profile(graph: nx.Graph) -> dict:
    profile = TopologyProfiler().profile(graph).to_dict()
    return {
        key: (None if isinstance(value, float) and math.isnan(value) else value)
        for key, value in profile.items()
    }


def _commit_sha() -> str | None:
    value = os.getenv("GITHUB_SHA")
    if value:
        return value
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_suite(
    output_path: str | Path = "results/canonical/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
) -> dict:
    """Run the canonical topology-aware development benchmark."""
    from experiments.generate_suite import build_suite

    started = time.perf_counter()
    graphs = build_suite()
    selector = HeuristicRegimeSelector()
    rows: list[dict] = []

    for name, graph in graphs.items():
        topology = _safe_profile(graph)
        regime = selector.classify(
            TopologyProfiler().profile(graph)
        )

        common = {
            "graph": name,
            "regime": regime,
            **topology,
        }

        for seed in seeds:
            rows.append(
                {
                    **common,
                    "strategy": "round_robin",
                    "seed": seed,
                    **balanced_round_robin(graph, k),
                }
            )
            rows.append(
                {
                    **common,
                    "strategy": "random_balanced",
                    "seed": seed,
                    **random_balanced(graph, k, seed),
                }
            )

            for variant in ("baseline", "affinity"):
                result = BLOCReloc(
                    graph,
                    k=k,
                    seed=seed,
                    variant=variant,
                ).refine(iterations=iterations)
                rows.append(
                    {
                        **common,
                        "strategy": f"bloc_reloc_{variant}",
                        "seed": seed,
                        "edge_cut": result.edge_cut,
                        "weighted_cost": result.weighted_cost,
                        "balance_error": result.balance_error,
                        "iterations": result.iterations,
                    }
                )

            if k == 2:
                rows.append(
                    {
                        **common,
                        "strategy": "kernighan_lin",
                        "seed": seed,
                        **kernighan_lin(graph, seed),
                    }
                )

    payload = {
        "schema_version": "0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "commit_sha": _commit_sha(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "objective": "unweighted edge cut for cross-strategy comparison",
        "graphs": {
            name: {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "density": nx.density(graph),
            }
            for name, graph in graphs.items()
        },
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_suite()
    print(
        f"Generated {len(result['rows'])} benchmark rows "
        f"across {len(result['graphs'])} graphs."
    )
