from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import networkx as nx


TOOLS = {
    "atof": {"packages": ["atof"], "description": "ATOF BLOC product path"},
    "atof_portfolio": {
        "packages": ["atof", "pymetis", "kahip"],
        "description": "ATOF open-source portfolio path",
    },
    "networkx": {"packages": ["networkx"], "description": "NetworkX Kernighan-Lin"},
    "metis": {"packages": ["networkx", "pymetis"], "description": "PyMetis multilevel bisection"},
    "kahip": {"packages": ["networkx", "kahip"], "description": "KaHIP KaFFPa Strong bisection"},
}


def build_graph() -> nx.Graph:
    return nx.Graph(nx.karate_club_graph())


def partition_for(tool: str, graph: nx.Graph, seed: int) -> tuple[dict, int]:
    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}

    if tool == "atof":
        from atof import optimize_graph

        result = optimize_graph(graph, k=2, seed=seed, iterations=25, variant="auto")
        partition = {str(node): int(block) for node, block in result.partition_result.partition.items()}
        payload = {
            "partition": partition,
            "edge_cut": int(result.partition_result.edge_cut),
            "balance_error": float(result.partition_result.balance_error),
        }
        return payload, payload["edge_cut"]

    if tool == "atof_portfolio":
        from atof import optimize_portfolio

        result = optimize_portfolio(graph, k=2, seed=seed, iterations=25)
        partition = {
            str(node): int(block)
            for node, block in result.selected_partition.items()
        }
        payload = {
            "partition": partition,
            "edge_cut": int(result.selected_edge_cut),
            "balance_error": float(result.selected_balance_error),
            "selected_backend": result.selected_strategy,
        }
        return payload, payload["edge_cut"]

    if tool == "networkx":
        from networkx.algorithms.community import kernighan_lin_bisection

        left, right = kernighan_lin_bisection(
            graph, partition=None, max_iter=25, weight=None, seed=seed
        )
        left = set(left)
        partition = {str(node): (0 if node in left else 1) for node in nodes}
        edge_cut = sum(partition[str(u)] != partition[str(v)] for u, v in graph.edges())
        balance_error = abs(len(left) - len(right)) / graph.number_of_nodes()
        payload = {
            "partition": partition,
            "edge_cut": int(edge_cut),
            "balance_error": float(balance_error),
        }
        return payload, payload["edge_cut"]

    adjacency = [[index[neighbor] for neighbor in graph.neighbors(node)] for node in nodes]

    if tool == "metis":
        import pymetis

        raw = pymetis.part_graph(
            2,
            adjacency=adjacency,
            tpwgts=[0.5, 0.5],
            recursive=True,
            options=pymetis.Options(seed=seed),
        )
        membership = list(raw.vertex_part)
    elif tool == "kahip":
        import kahip

        xadj = [0]
        adjncy: list[int] = []
        for node in nodes:
            adjncy.extend(index[neighbor] for neighbor in graph.neighbors(node))
            xadj.append(len(adjncy))
        _, membership = kahip.kaffpa(
            [1] * len(nodes),
            xadj,
            [1] * len(adjncy),
            adjncy,
            2,
            0.03,
            1,
            int(seed),
            2,
        )
        membership = [int(block) for block in membership]
    else:
        raise ValueError(f"unknown tool: {tool}")

    partition = {str(node): int(membership[index[node]]) for node in nodes}
    edge_cut = sum(partition[str(u)] != partition[str(v)] for u, v in graph.edges())
    balance_error = abs(membership.count(0) - membership.count(1)) / graph.number_of_nodes()
    payload = {
        "partition": partition,
        "edge_cut": int(edge_cut),
        "balance_error": float(balance_error),
    }
    return payload, payload["edge_cut"]


def package_version(tool: str) -> dict[str, str | None]:
    names = {
        "atof": ["atof"],
        "atof_portfolio": ["atof", "pymetis", "kahip"],
        "networkx": ["networkx"],
        "metis": ["pymetis", "networkx"],
        "kahip": ["kahip", "networkx"],
    }[tool]
    versions: dict[str, str | None] = {}
    for name in names:
        module = importlib.import_module(name)
        versions[name] = getattr(module, "__version__", None)
    return versions


def measure(tool: str) -> dict:
    graph = build_graph()
    seed = 42

    import_start = time.perf_counter()
    versions = package_version(tool)
    import_seconds = time.perf_counter() - import_start

    first_start = time.perf_counter()
    first_result, _ = partition_for(tool, graph, seed)
    first_partition_seconds = time.perf_counter() - first_start

    repeated_partition_seconds: list[float] = []
    repeated_results: list[dict] = []
    for repeat_seed in (42, 101, 2024):
        started = time.perf_counter()
        result, _ = partition_for(tool, graph, repeat_seed)
        repeated_partition_seconds.append(time.perf_counter() - started)
        repeated_results.append(result)

    return {
        "schema_version": "0.1",
        "tool": tool,
        "description": TOOLS[tool]["description"],
        "python": sys.version,
        "platform": platform.platform(),
        "graph": {
            "name": "karate_club_graph",
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "k": 2,
        },
        "versions": versions,
        "import_seconds": import_seconds,
        "first_partition_seconds": first_partition_seconds,
        "repeated_partition_seconds": repeated_partition_seconds,
        "first_result": first_result,
        "repeated_results": repeated_results,
        "selected_backend": first_result.get("selected_backend"),

        "determinism_check": repeated_results[0] == partition_for(tool, graph, seed)[0],
        "setup_seconds": float(os.environ.get("ATOF_SETUP_SECONDS", "nan")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", choices=tuple(TOOLS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = measure(args.tool)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "tool": payload["tool"],
        "setup_seconds": payload["setup_seconds"],
        "import_seconds": payload["import_seconds"],
        "first_partition_seconds": payload["first_partition_seconds"],
        "edge_cut": payload["first_result"]["edge_cut"],
        "balance_error": payload["first_result"]["balance_error"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
