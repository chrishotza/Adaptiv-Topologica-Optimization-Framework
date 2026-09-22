from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

from .backends import _run_kaminpar_in_process, _run_mtkahypar_in_process


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=("kaminpar", "mtkahypar"), required=True)
    parser.add_argument("--context", default="default")
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--graph-id", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--k", type=int, required=True)
    args = parser.parse_args()

    with args.graph.open("rb") as handle:
        graph = pickle.load(handle)

    if args.strategy == "kaminpar":
        partition, edge_cut, balance, runtime = _run_kaminpar_in_process(
            graph,
            graph_id=args.graph_id,
            seed=args.seed,
            k=args.k,
            context_name=args.context,
        )
    else:
        partition, edge_cut, balance, runtime = _run_mtkahypar_in_process(
            graph,
            graph_id=args.graph_id,
            seed=args.seed,
            k=args.k,
            preset=args.context,
        )

    nodes = list(graph.nodes())
    membership = [int(partition[node]) for node in nodes]
    print(
        json.dumps(
            {
                "nodes": len(nodes),
                "membership": membership,
                "edge_cut": int(edge_cut),
                "balance_error": float(balance),
                "backend_runtime_seconds": float(runtime),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
