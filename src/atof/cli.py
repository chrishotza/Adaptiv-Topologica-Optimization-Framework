from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

from . import __version__
from .comparison import compare_graph, compact_comparison
from .ai import build_ai_manifest, build_doctor_report, compact_json, compact_result
from .portfolio import optimize_portfolio
from .product import (
    PARTITION_OUTPUT_FORMATS,
    SUPPORTED_INPUT_FORMATS,
    load_graph,
    optimize_graph,
    write_partition,
    write_partition_mapping,
)
from .provenance import graph_fingerprint
from .selector import HeuristicRegimeSelector
from .topology import TopologyProfiler


_FORMAT_CHOICES = SUPPORTED_INPUT_FORMATS
_ENGINE_CHOICES = ("bloc", "portfolio")
_BLOC_VARIANT_CHOICES = ("auto", "baseline", "affinity")

_CLI_ERRORS = (OSError, ValueError, RuntimeError, TypeError, UnicodeError, SyntaxError, nx.NetworkXException)


def _emit_error(exc: Exception) -> int:
    payload = {
        "schema": "atof.error.v1",
        "name": "atof",
        "version": __version__,
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
    }
    print(compact_json(payload))
    return 2


def _profile(path: Path, format: str = "auto") -> dict:
    graph = load_graph(path, format=format)
    profile = TopologyProfiler().profile(graph)
    recommendation = HeuristicRegimeSelector().recommend(profile)
    return {
        "file": str(path),
        "version": __version__,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
        "topology": profile.to_dict(),
        "recommendation": {
            "mode": "heuristic",
            "regime": recommendation.regime,
            "primary": recommendation.primary,
            "alternatives": list(recommendation.alternatives),
            "rationale": recommendation.rationale,
        },
        "provenance": {
            "graph_fingerprint": graph_fingerprint(graph),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atof",
        description="Adaptive Topological Optimization Framework",
    )
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    ai_parser = subparsers.add_parser("ai", help="emit the AI capability manifest")
    ai_parser.add_argument("--full", "-F", action="store_true")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="inspect runtime and backend availability",
    )
    doctor_parser.add_argument("--full", "-F", action="store_true")

    solve_parser = subparsers.add_parser(
        "solve",
        help="short AI-friendly alias for portfolio optimization",
    )
    solve_parser.add_argument("path", type=Path)
    solve_parser.add_argument("--k", "-k", type=int, default=2)
    solve_parser.add_argument("--seed", "-s", type=int, default=42)
    solve_parser.add_argument("--iterations", "-i", type=int, default=25)
    solve_parser.add_argument("--format", "-f", choices=_FORMAT_CHOICES, default="auto")
    solve_parser.add_argument("--output", "-o", type=Path)
    solve_parser.add_argument("--partition-output", "-p", type=Path)
    solve_parser.add_argument(
        "--partition-format",
        choices=PARTITION_OUTPUT_FORMATS,
        default="auto",
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="compare native Engine and Portfolio under identical parameters",
    )
    compare_parser.add_argument("path", type=Path)
    compare_parser.add_argument("--k", "-k", type=int, default=2)
    compare_parser.add_argument("--seed", "-s", type=int, default=42)
    compare_parser.add_argument("--iterations", "-i", type=int, default=25)
    compare_parser.add_argument("--format", "-f", choices=_FORMAT_CHOICES, default="auto")
    compare_parser.add_argument("--output", "-o", type=Path)
    compare_parser.add_argument("--compact", "-c", action="store_true")

    profile_parser = subparsers.add_parser("profile", help="profile a graph")
    profile_parser.add_argument("path", type=Path)
    profile_parser.add_argument("--format", "-f", choices=_FORMAT_CHOICES, default="auto")
    profile_parser.add_argument("--compact", "-c", action="store_true")

    optimize_parser = subparsers.add_parser(
        "optimize",
        help="profile and partition a graph",
    )
    optimize_parser.add_argument("path", type=Path)
    optimize_parser.add_argument("--k", "-k", type=int, default=2)
    optimize_parser.add_argument("--seed", "-s", type=int, default=42)
    optimize_parser.add_argument("--iterations", "-i", type=int, default=25)
    optimize_parser.add_argument(
        "--engine",
        "-e",
        choices=_ENGINE_CHOICES,
        default="bloc",
        help="portfolio compares available open-source backends under one contract",
    )
    optimize_parser.add_argument(
        "--variant",
        "-v",
        choices=_BLOC_VARIANT_CHOICES,
        default="auto",
        help="BLOC-RELOC variant when --engine bloc is used",
    )
    optimize_parser.add_argument("--format", "-f", choices=_FORMAT_CHOICES, default="auto")
    optimize_parser.add_argument("--output", "-o", type=Path)
    optimize_parser.add_argument("--compact", "-c", action="store_true")
    optimize_parser.add_argument("--partition-output", "-p", type=Path)
    optimize_parser.add_argument(
        "--partition-format",
        choices=PARTITION_OUTPUT_FORMATS,
        default="auto",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "ai":
        payload = build_ai_manifest(full=args.full)
        print(
            json.dumps(payload, indent=2, sort_keys=True)
            if args.full
            else compact_json(payload)
        )
        return 0

    if args.command == "doctor":
        payload = build_doctor_report(full=args.full)
        print(
            json.dumps(payload, indent=2, sort_keys=True)
            if args.full
            else compact_json(payload)
        )
        return 0

    if args.command == "solve":
        try:
            graph = load_graph(args.path, format=args.format)
            result = optimize_portfolio(
                graph,
                k=args.k,
                seed=args.seed,
                iterations=args.iterations,
            )
            if args.partition_output is not None:
                write_partition_mapping(
                    result.selected_partition,
                    args.partition_output,
                    format=args.partition_format,
                )
            payload = compact_result(result.to_dict())
            encoded = compact_json(payload)
            if args.output is None:
                print(encoded)
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(encoded + "\n", encoding="utf-8")
                print(str(args.output))
            return 0
        except _CLI_ERRORS as exc:
            return _emit_error(exc)

    if args.command == "compare":
        try:
            graph = load_graph(args.path, format=args.format)
            payload = compare_graph(
                graph,
                k=args.k,
                seed=args.seed,
                iterations=args.iterations,
            )
            rendered = compact_comparison(payload) if args.compact else payload
            encoded = compact_json(rendered) if args.compact else json.dumps(
                rendered,
                indent=2,
                sort_keys=True,
            )
            if args.output is None:
                print(encoded)
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(encoded + "\n", encoding="utf-8")
                print(str(args.output))
            return 0
        except _CLI_ERRORS as exc:
            return _emit_error(exc)

    if args.command == "profile":
        try:
            payload = _profile(args.path, args.format)
            if args.compact:
                compact = {
                    "mode": "profile",
                    "version": payload["version"],
                    "graph": payload["graph"],
                    "recommendation": {
                        "regime": payload["recommendation"]["regime"],
                        "primary": payload["recommendation"]["primary"],
                        "alternatives": payload["recommendation"]["alternatives"],
                    },
                    "provenance": payload["provenance"],
                }
                print(compact_json(compact))
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        except _CLI_ERRORS as exc:
            return _emit_error(exc)

    if args.command == "optimize":
        try:
            if args.engine == "portfolio" and args.variant != "auto":
                raise ValueError("--variant applies only to --engine bloc")
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
                encoded = compact_json(compact_result(payload))
            else:
                encoded = json.dumps(payload, indent=2, sort_keys=True)
            if args.partition_output is not None:
                if args.engine == "bloc":
                    write_partition(result, args.partition_output, format=args.partition_format)
                else:
                    write_partition_mapping(
                        result.selected_partition,
                        args.partition_output,
                        format=args.partition_format,
                    )
            if args.output is None:
                print(encoded)
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(encoded + "\n", encoding="utf-8")
                print(str(args.output))
            return 0
        except _CLI_ERRORS as exc:
            return _emit_error(exc)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
