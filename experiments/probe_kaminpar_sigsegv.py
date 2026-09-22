from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import networkx as nx


CONTEXTS = (
    "default",
    "strong",
    "fast",
    "largek",
    "largek-strong",
    "largek-fast",
)
K_VALUES = (4, 8, 32, 64)
EPSILONS = (0.0, 0.03)


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(index[neighbor] for neighbor in graph.neighbors(node))
        lines.append(" ".join(str(value) for value in neighbors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _worker(graph_path: str, context: str, k: int, epsilon: float) -> int:
    import kaminpar

    graph = kaminpar.load_graph(
        graph_path,
        kaminpar.GraphFileFormat.METIS,
        compress=False,
    )
    instance = kaminpar.KaMinPar(
        num_threads=1,
        ctx=kaminpar.context_by_name(context),
    )
    kaminpar.reseed(42)
    partition = instance.compute_partition(graph, k=k, eps=epsilon)
    print(
        json.dumps(
            {
                "context": context,
                "k": k,
                "epsilon": epsilon,
                "nodes": len(partition),
            }
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--context")
    parser.add_argument("--k", type=int)
    parser.add_argument("--epsilon", type=float)
    args = parser.parse_args()

    if args.worker:
        if args.graph is None or args.context is None or args.k is None or args.epsilon is None:
            raise SystemExit("worker requires --graph, --context, --k and --epsilon")
        return _worker(str(args.graph), args.context, args.k, args.epsilon)

    graph = nx.barabasi_albert_graph(64, 3, seed=42)
    with tempfile.TemporaryDirectory(prefix="atof-kaminpar-probe-") as tmp:
        graph_path = Path(tmp) / "barabasi_albert.metis"
        _write_metis_graph(graph, graph_path)

        rows = []
        for context in CONTEXTS:
            for k in K_VALUES:
                for epsilon in EPSILONS:
                    command = [
                        sys.executable,
                        __file__,
                        "--worker",
                        "--graph",
                        str(graph_path),
                        "--context",
                        context,
                        "--k",
                        str(k),
                        "--epsilon",
                        str(epsilon),
                    ]
                    completed = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        env={**os.environ, "PYTHONUNBUFFERED": "1"},
                    )
                    row = {
                        "context": context,
                        "k": k,
                        "epsilon": epsilon,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout.strip(),
                        "stderr": completed.stderr.strip(),
                    }
                    rows.append(row)
                    print(json.dumps(row, sort_keys=True), flush=True)

    failures = [row for row in rows if row["returncode"] != 0]
    print(
        json.dumps(
            {
                "total": len(rows),
                "failures": len(failures),
                "failures_by_context": {
                    context: sum(1 for row in failures if row["context"] == context)
                    for context in CONTEXTS
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
