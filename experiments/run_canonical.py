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
import numpy as np

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



def _balanced_spectral_order(
    graph: nx.Graph, *, modularity: bool = False
) -> tuple[list, list]:
    """Return nodes and a deterministic spectral ranking.

    Graphs up to 2000 nodes use the historical dense NumPy implementation.
    Larger graphs switch to SciPy sparse eigensolvers so the same strategy
    remains defined on the expanded scalability corpus without changing the
    balanced ranking contract.
    """
    node_count = graph.number_of_nodes()
    nodes = list(graph.nodes())

    if node_count <= 2000:
        adjacency = nx.to_numpy_array(graph, nodelist=nodes, dtype=float)
        if modularity:
            degrees = adjacency.sum(axis=1)
            edge_count = graph.number_of_edges()
            if edge_count == 0:
                leading = degrees
            else:
                matrix = adjacency - np.outer(degrees, degrees) / (2.0 * edge_count)
                _, eigenvectors = np.linalg.eigh(matrix)
                leading = eigenvectors[:, -1]
        else:
            laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
            _, eigenvectors = np.linalg.eigh(laplacian)
            leading = eigenvectors[:, 1]
    else:
        from scipy.sparse import csr_matrix
        from scipy.sparse.linalg import LinearOperator, eigsh

        adjacency = nx.to_scipy_sparse_array(
            graph, nodelist=nodes, dtype=float, format="csr"
        )
        if modularity:
            degrees = np.asarray(adjacency.sum(axis=1)).ravel()
            edge_count = graph.number_of_edges()
            if edge_count == 0:
                leading = degrees
            else:
                degree_column = degrees

                def matvec(vector: np.ndarray) -> np.ndarray:
                    return adjacency @ vector - degree_column * (
                        float(degree_column @ vector) / (2.0 * edge_count)
                    )

                operator = LinearOperator(
                    shape=(node_count, node_count),
                    matvec=matvec,
                    dtype=float,
                )
                _, eigenvectors = eigsh(
                    operator,
                    k=1,
                    which="LA",
                    v0=np.ones(node_count, dtype=float),
                    tol=1e-8,
                    maxiter=max(1000, node_count * 10),
                )
                leading = eigenvectors[:, 0]
        else:
            laplacian = csr_matrix(
                np.diag(np.asarray(adjacency.sum(axis=1)).ravel())
            ) - adjacency
            _, eigenvectors = eigsh(
                laplacian,
                k=2,
                which="SM",
                v0=np.ones(node_count, dtype=float),
                tol=1e-8,
                maxiter=max(1000, node_count * 10),
            )
            order_eigenvalues = np.argsort(np.asarray(_))
            leading = eigenvectors[:, int(order_eigenvalues[1])]

    order = sorted(
        range(node_count),
        key=lambda index: (float(leading[index]), repr(nodes[index])),
    )
    return nodes, order


def spectral_bisection(graph: nx.Graph) -> dict:
    """Deterministic balanced spectral bisection.

    Dense NumPy eigendecomposition is retained for moderate graphs; large
    graphs use a sparse SciPy eigensolver to preserve the strategy on the
    scalability corpus.
    """
    node_count = graph.number_of_nodes()
    if node_count < 2:
        raise ValueError("spectral bisection requires at least two nodes")

    nodes, order = _balanced_spectral_order(graph, modularity=False)
    left_size = node_count // 2
    partition = {
        nodes[index]: 0 if position < left_size else 1
        for position, index in enumerate(order)
    }
    cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return {
        "edge_cut": int(cut),
        "balance_error": 0.0,
        "weighted_cost": float(cut),
    }


def spectral_modularity_bisection(graph: nx.Graph) -> dict:
    """Balanced bisection from the leading modularity-matrix eigenvector.

    The sign cut of the modularity eigenvector is converted to a balanced
    floor/ceil split by ranking its entries. This preserves the spectral
    signal while keeping the benchmark's exact balance contract.
    """
    node_count = graph.number_of_nodes()
    if node_count < 2:
        raise ValueError("spectral modularity bisection requires at least two nodes")

    nodes, order = _balanced_spectral_order(graph, modularity=True)
    left_size = node_count // 2
    partition = {
        nodes[index]: 0 if position < left_size else 1
        for position, index in enumerate(order)
    }
    cut = sum(partition[u] != partition[v] for u, v in graph.edges())
    return {
        "edge_cut": int(cut),
        "balance_error": 0.0,
        "weighted_cost": float(cut),
    }

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
                        "strategy": "spectral_bisection",
                        "seed": seed,
                        **spectral_bisection(graph),
                    }
                )
                rows.append(
                    {
                        **common,
                        "strategy": "spectral_modularity_bisection",
                        "seed": seed,
                        **spectral_modularity_bisection(graph),
                    }
                )
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
