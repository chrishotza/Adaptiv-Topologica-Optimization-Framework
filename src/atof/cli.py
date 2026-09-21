from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

from .selector import HeuristicRegimeSelector
from .topology import TopologyProfiler
from . import __version__


def _profile(path: Path) -> dict:
    graph = nx.read_edgelist(path, nodetype=int, data=False)
    profiler = TopologyProfiler()
    profile = profiler.profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(profile)

    return {
        "file": str(path),
        "version": __version__,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "topology": profile.to_dict(),
        "recommendation": {
            "regime": recommendation.regime,
            "primary": recommendation.primary,
            "alternatives": list(recommendation.alternatives),
            "rationale": recommendation.rationale,
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
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "profile":
        print(json.dumps(_profile(args.path), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
