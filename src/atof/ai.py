from __future__ import annotations

import json

from . import __version__
from .backends import inspect_backends
from .provenance import runtime_metadata


def build_ai_manifest(*, full: bool = False) -> dict:
    """Return a compact, stable context contract for AI agents and automation."""
    manifest = {
        "schema": "atof.ai.v1",
        "name": "atof",
        "version": __version__,
        "purpose": "Open-source graph optimization interface for machine-operable graph partitioning.",
        "primary_flow": "ai -> doctor -> solve -> compact JSON -> full evidence on demand",
        "commands": {
            "ai": "atof ai",
            "doctor": "atof doctor",
            "solve": "atof solve <graph>",
            "module": "python -m atof",
            "profile": "atof profile <graph>",
            "optimize": "atof optimize <graph> --engine portfolio",
            "version": "atof --version",
            "short_flags": {
                "compact": "-c",
                "engine": "-e",
                "seed": "-s",
                "iterations": "-i",
                "format": "-f",
                "output": "-o",
                "partition_output": "-p",
                "full": "-F"
            },
        },
        "input": {
            "formats": ["edgelist", "json", "graphml", "gexf", "gml"],
            "default_format": "auto",
            "default_seed": 42,
            "stdin": {"path": "-", "formats": ["edgelist", "json"]},
            "json": {"nodes": "optional array of node IDs", "edges": "array of 2-item node-ID arrays"},
        },
        "capabilities": {
            "portfolio": {
                "k": 2,
                "objective": "minimize unweighted edge cut subject to balanced two-way partition",
                "backends": [
                    "BLOC-RELOC",
                    "NetworkX Kernighan-Lin",
                    "METIS via PyMetis (optional)",
                    "KaHIP via KaFFPa-Strong (optional)",
                ],
                "selection": "empirical minimum observed edge_cut; ties prefer balance, runtime, name",
            },
            "exports": ["JSON result", "node-to-block JSON", "node-to-block CSV", "node-to-block TSV"],
            "provenance": ["graph SHA-256 fingerprint", "seed", "parameters", "backend availability"],
        },
        "output": {
            "default": "JSON",
            "compact": "low-token graph/result summary",
            "full": "topology, candidates, provenance, and selected node-to-block mapping",
        },
        "claim_policy": {
            "rule": "claims are tied to code, tests, or named benchmarks",
            "non_claims": [
                "not universally optimal",
                "not universally faster",
                "not a replacement for every specialized partitioner",
            ],
        },
        "limits": [
            "portfolio mode currently supports k=2",
            "current common objective is unweighted edge cut",
            "weight attributes are accepted as input metadata but ignored by the current unweighted objective",
            "weighted and multiway portfolio optimization are outside the current MVP contract",
        ],
    }
    return manifest if full else {
        "schema": manifest["schema"],
        "name": manifest["name"],
        "version": manifest["version"],
        "purpose": manifest["purpose"],
        "commands": manifest["commands"],
        "input": manifest["input"],
        "capabilities": manifest["capabilities"],
        "output": manifest["output"],
        "claim_policy": manifest["claim_policy"],
        "limits": manifest["limits"],
    }


def build_doctor_report(*, full: bool = False) -> dict:
    """Describe the current execution environment and backend availability."""
    backends = [item.to_dict() for item in inspect_backends()]
    report = {
        "schema": "atof.doctor.v1",
        "name": "atof",
        "version": __version__,
        "runtime": runtime_metadata(),
        "backends": backends,
        "input_formats": ["edgelist", "graphml", "gexf", "gml"],
        "portfolio_ready": any(
            item["available"] and item["id"] == "networkx-kl"
            for item in backends
        ),
    }
    if not full:
        report["runtime"] = {
            "python": report["runtime"]["python"],
            "platform": report["runtime"]["platform"],
        }
    return report


def compact_result(payload: dict) -> dict:
    """Reduce a product result to the fields most useful for an agent."""
    result = payload.get("result", {})
    strategy = payload.get("strategy", {})
    graph = payload.get("graph", {})
    compact = {
        "mode": payload.get("mode"),
        "version": payload.get("version", __version__),
        "graph": {
            "nodes": graph.get("nodes"),
            "edges": graph.get("edges"),
        },
        "strategy": strategy,
        "result": {
            "k": result.get("k"),
            "edge_cut": result.get("edge_cut"),
            "balance_error": result.get("balance_error"),
        },
    }
    provenance = payload.get("provenance")
    if provenance is not None:
        compact["provenance"] = provenance
    parameters = payload.get("parameters")
    if parameters is not None:
        compact["parameters"] = parameters
    candidates = payload.get("candidates")
    if candidates is not None:
        compact["candidates"] = [
            {
                "id": c.get("id", c.get("name")),
                "name": c.get("name"),
                "available": c.get("available"),
                "edge_cut": c.get("edge_cut"),
                "runtime_seconds": c.get("runtime_seconds"),
                "error": c.get("error"),
            }
            for c in candidates
        ]
    return compact


def compact_json(payload: dict) -> str:
    """Encode an AI-facing payload without whitespace overhead."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
