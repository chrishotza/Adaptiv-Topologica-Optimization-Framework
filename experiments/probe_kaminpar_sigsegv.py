from __future__ import annotations

import argparse
import json
import math
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
SEEDS = (42, 101, 2024)


def _write_metis_graph(graph: nx.Graph, path: Path) -> None:
    nodes = list(graph.nodes())
    index = {node: i + 1 for i, node in enumerate(nodes)}
    lines = [f"{len(nodes)} {graph.number_of_edges()}"]
    for node in nodes:
        neighbors = sorted(index[neighbor] for neighbor in graph.neighbors(node))
        lines.append(" ".join(str(value) for value in neighbors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _worker(
    graph_path: str,
    context: str,
    k: int,
    epsilon: float,
    seed: int,
) -> int:
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
    kaminpar.reseed(int(seed))
    if epsilon == 0.0:
        max_block_weight = math.ceil(graph.n() / k)
        partition = instance.compute_partition(
            graph, [max_block_weight] * k
        )
        constraint_mode = "absolute_max_block_weight"
    else:
        partition = instance.compute_partition(graph, k=k, eps=epsilon)
        constraint_mode = "epsilon"
    print(
        json.dumps(
            {
                "context": context,
                "k": k,
                "epsilon": epsilon,
                "constraint_mode": constraint_mode,
                "solver_seed": seed,
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
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/kaminpar_sigsegv_probe.json"),
    )
    args = parser.parse_args()

    if args.worker:
        if (
            args.graph is None
            or args.context is None
            or args.k is None
            or args.epsilon is None
            or args.seed is None
        ):
            raise SystemExit(
                "worker requires --graph, --context, --k, --epsilon and --seed"
            )
        return _worker(
            str(args.graph),
            args.context,
            args.k,
            args.epsilon,
            args.seed,
        )

    graph = nx.barabasi_albert_graph(64, 3, seed=42)
    with tempfile.TemporaryDirectory(prefix="atof-kaminpar-probe-") as tmp:
        graph_path = Path(tmp) / "barabasi_albert.metis"
        _write_metis_graph(graph, graph_path)

        rows = []
        for context in CONTEXTS:
            for k in K_VALUES:
                for epsilon in EPSILONS:
                    for seed in SEEDS:
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
                            "--seed",
                            str(seed),
                        ]
                        completed = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            env={**os.environ, "PYTHONUNBUFFERED": "1"},
                        )
                        row = {
                            "graph": "development/barabasi_albert",
                            "graph_seed": 42,
                            "solver_seed": seed,
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
    summary = {
        "graph": "development/barabasi_albert",
        "graph_seed": 42,
        "solver_seeds": list(SEEDS),
        "contexts": list(CONTEXTS),
        "k_values": list(K_VALUES),
        "epsilons": list(EPSILONS),
        "total": len(rows),
        "expected_total": len(CONTEXTS) * len(K_VALUES) * len(EPSILONS) * len(SEEDS),
        "failures": len(failures),
        "failures_by_context": {
            context: sum(1 for row in failures if row["context"] == context)
            for context in CONTEXTS
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "total": summary["total"],
                "expected_total": summary["expected_total"],
                "failures": summary["failures"],
                "failures_by_context": summary["failures_by_context"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if summary["total"] != summary["expected_total"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
