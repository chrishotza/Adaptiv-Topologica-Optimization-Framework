from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .ai import build_ai_manifest, compact_result
from .product import load_graph, optimize_graph
from .portfolio import optimize_portfolio
from .topology import TopologyProfiler
from .selector import HeuristicRegimeSelector


def _profile(path: Path, format: str = "auto") -> dict:
    graph = load_graph(path, format=format)
    profile = TopologyProfiler().profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(profile)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atof",
        description="Adaptive Topological Optimization Framework",
    )
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    ai_parser = subparsers.add_parser(
        "ai",
        help="emit a compact AI/automation contract",
    )
    ai_parser.add_argument(
        "--full",
        action="store_true",
        help="emit the expanded AI manifest",
    )

    profile_parser = subparsers.add_parser(
        "profile",
        help="profile a graph",
    )
    profile_parser.add_argument("path", type=Path)
    profile_parser.add_argument(
        "--format",
        choices=("auto", "edgelist", "graphml", "gexf", "gml"),
        default="auto",
    )
    profile_parser.add_argument(
        "--compact",
        action="store_true",
        help="emit only the low-token profile summary",
    )

    optimize_parser = subparsers.add_parser(
        "optimize",
        help="profile and partition a graph",
    )
    optimize_parser.add_argument("path", type=Path)
    optimize_parser.add_argument("--k", type=int, default=2)
    optimize_parser.add_argument("--seed", type=int, default=42)
    optimize_parser.add_argument("--iterations", type=int, default=25)
    optimize_parser.add_argument(
        "--engine",
        choices=("bloc", "portfolio"),
        default="bloc",
        help="portfolio compares available open-source backends under one contract",
    )
    optimize_parser.add_argument(
        "--variant",
        choices=("auto", "baseline", "affinity"),
        default="auto",
        help="BLOC-RELOC variant when --engine bloc is used",
    )
    optimize_parser.add_argument(
        "--format",
        choices=("auto", "edgelist", "graphml", "gexf", "gml"),
        default="auto",
    )
    optimize_parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output path; stdout is used when omitted",
    )
    optimize_parser.add_argument(
        "--compact",
        action="store_true",
        help="emit only the low-token result summary",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "ai":
        payload = build_ai_manifest(full=args.full)
        if args.full:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        return 0

    if args.command == "profile":
        payload = _profile(args.path, args.format)
        if args.compact:
            payload = {
                "mode": "profile",
                "version": payload["version"],
                "graph": {
                    "nodes": payload["nodes"],
                    "edges": payload["edges"],
                },
                "recommendation": payload["recommendation"],
            }
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "optimize":
        graph = load_graph(args.path, format=args.format)
        if args.engine == "portfolio":
            result = optimize_portfolio(
                graph,
                k=args.k,
                seed=args.seed,
                iterations=args.iterations,
            )
        else:
            result = optimize_graph(
                graph,
                k=args.k,
                seed=args.seed,
                iterations=args.iterations,
                variant=args.variant,
            )
        payload = result.to_dict()
        payload["file"] = str(args.path)
        payload["version"] = __version__
        if args.compact:
            payload = compact_result(payload)
            encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        else:
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
