from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

from . import __version__
from .selector import HeuristicRegimeSelector
from .strategies import BLOCReloc
from .topology import TopologyProfiler


def _load_graph(path: Path) -> nx.Graph:
    if not path.exists():
        raise FileNotFoundError(path)
    return nx.read_edgelist(path, data=False)


def _profile_payload(graph: nx.Graph):
    profile = TopologyProfiler().profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(profile)
    return profile, recommendation


def _recommendation_variant(primary: str) -> str:
    return "affinity" if primary.endswith("(affinity)") else "baseline"


def _profile(path: Path) -> dict:
    graph = _load_graph(path)
    profile, recommendation = _profile_payload(graph)

    return {
        "file": str(path),
        "version": __version__,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "topology": profile.to_dict(),
        "recommendation": {
            "mode": "heuristic",
            "regime": recommendation.regime,
            "primary": recommendation.primary,
            "alternatives": list(recommendation.alternatives),
            "rationale": recommendation.rationale,
        },
    }


def _optimize(path: Path, *, k: int, seed: int, iterations: int, variant: str) -> dict:
    graph = _load_graph(path)
    profile, recommendation = _profile_payload(graph)
    selected_variant = (
        _recommendation_variant(recommendation.primary)
        if variant == "auto"
        else variant
    )

    result = BLOCReloc(
        graph,
        k=k,
        seed=seed,
        variant=selected_variant,
    ).refine(iterations=iterations)

    block_sizes: dict[str, int] = {}
    for block in result.partition.values():
        block_sizes[str(block)] = block_sizes.get(str(block), 0) + 1

    return {
        "file": str(path),
        "version": __version__,
        "mode": "optimize",
        "strategy": {
            "requested": variant,
            "selected": f"BLOCReloc({selected_variant})",
            "selection_mode": "heuristic" if variant == "auto" else "explicit",
            "regime": recommendation.regime,
        },
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
        "topology": profile.to_dict(),
        "recommendation": {
            "primary": recommendation.primary,
            "alternatives": list(recommendation.alternatives),
            "rationale": recommendation.rationale,
        },
        "result": {
            "k": k,
            "seed": seed,
            "iterations": result.iterations,
            "edge_cut": result.edge_cut,
            "weighted_cost": result.weighted_cost,
            "balance_error": result.balance_error,
            "accepted_moves": result.accepted_moves,
            "rejected_moves": result.rejected_moves,
            "block_sizes": block_sizes,
            "partition": {
                str(node): block for node, block in result.partition.items()
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atof",
        description="Adaptive Topological Optimization Framework",
    )
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    profile_parser = subparsers.add_parser(
        "profile",
        help="profile a whitespace-delimited edge-list graph",
    )
    profile_parser.add_argument("path", type=Path)

    optimize_parser = subparsers.add_parser(
        "optimize",
        help="profile and partition a whitespace-delimited edge-list graph",
    )
    optimize_parser.add_argument("path", type=Path)
    optimize_parser.add_argument("--k", type=int, default=2)
    optimize_parser.add_argument("--seed", type=int, default=42)
    optimize_parser.add_argument("--iterations", type=int, default=25)
    optimize_parser.add_argument(
        "--variant",
        choices=("auto", "baseline", "affinity"),
        default="auto",
        help="auto uses the transparent heuristic selector",
    )
    optimize_parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output path; stdout is used when omitted",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "profile":
        print(json.dumps(_profile(args.path), indent=2))
        return 0

    if args.command == "optimize":
        payload = _optimize(
            args.path,
            k=args.k,
            seed=args.seed,
            iterations=args.iterations,
            variant=args.variant,
        )
        encoded = json.dumps(payload, indent=2, sort_keys=True)
        if args.output is None:
            print(encoded)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
            print(str(args.output))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
