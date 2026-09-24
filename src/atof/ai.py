from __future__ import annotations

import json

from . import __version__
from .backends import inspect_backends
from .provenance import runtime_metadata
from .product import SUPPORTED_INPUT_FORMATS


def build_ai_manifest(*, full: bool = False) -> dict:
    """Return a compact, stable context contract for AI agents and automation."""
    manifest = {
        "schema": "atof.ai.v1",
        "name": "atof",
        "version": __version__,
        "purpose": "AI-first graph optimization interface.",
        "primary_flow": "ai->doctor->solve->compact JSON",
        "commands": {
            "ai": "atof ai",
            "doctor": "atof doctor",
            "solve": "atof solve <graph> [--k N]",
            "compare": "atof compare <graph> [--k N]",
            "module": "python -m atof",
            "profile": "atof profile <graph>",
            "optimize": "atof optimize <graph> --engine portfolio",
            "version": "atof --version",
            "short_flags": {
                "compact": "-c",
                "k": "-k",
                "engine": "-e",
                "seed": "-s",
                "iterations": "-i",
                "format": "-f",
                "output": "-o",
                "partition_output": "-p",
                "full": "-F",
            },
        },
        "input": {
            "formats": [item for item in SUPPORTED_INPUT_FORMATS if item != "auto"],
            "default_format": "auto",
            "default_seed": 42,
            "stdin": {"path": "-", "formats": ["edgelist", "json"]},
            "json": {
                "nodes": "optional array of node IDs",
                "edges": "array of 2-item node-ID arrays",
            },
            "node_id_serialization": "partition outputs canonicalize node IDs with str(); collisions after string conversion are rejected",
        },
        "capabilities": {
            "engine": {
                "k": ">=2",
                "result_schema": "atof.optimize.v1",
                "objective": (
                    "reports unweighted edge_cut; baseline minimizes unweighted "
                    "edge_cut, while affinity minimizes a degree-affinity weighted surrogate"
                ),
                "backend": "BLOC-RELOC",
                "variants": {
                    "baseline": "direct unweighted edge-cut minimization",
                    "affinity": (
                        "degree-affinity weighted surrogate; final edge_cut remains "
                        "the unweighted reported metric"
                    ),
                    "auto": "heuristically selects baseline or affinity",
                },
            },
            "comparison": {
                "result_schema": "atof.compare.v1",
                "scope": "Engine vs Portfolio",
            },
            "portfolio": {
                "k": ">=2",
                "result_schema": "atof.portfolio.v1",
                "objective": "minimize unweighted edge cut subject to balanced k-way partition",
                "backends": [
                    "bloc",
                    "networkx-kl",
                    "metis",
                    "kahip",
                    "kaminpar",
                    "kaminpar-strong",
                    "mtkahypar",
                    "mtkahypar-quality",
                ],
                "selection": "empirical minimum observed edge_cut; ties prefer balance, runtime, name",
            },
            "exports": [
                "JSON result",
                "node-to-block JSON",
                "node-to-block CSV",
                "node-to-block TSV",
            ],
            "provenance": [
                "graph SHA-256 fingerprint",
                "seed",
                "parameters",
                "backend availability",
            ],
        },
        "output": {
            "default": "JSON",
            "compact": "low-token graph/result summary",
            "full": "topology, candidates, provenance, and selected node-to-block mapping",
            "objective_metric_rule": "In Engine mode, objective.optimization_metric names the optimized scalar; result.weighted_cost is the internal reported objective value and is not an input edge-weight cost.",
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
            "backends use stable IDs",
            "portfolio mode supports k>=2; NetworkX Kernighan-Lin is available only for k=2",
            "current common portfolio objective is unweighted edge cut",
            "Engine affinity uses a degree-affinity weighted surrogate and reports unweighted edge_cut",
            "weight attributes are accepted as input metadata but ignored by the current unweighted graph model",
            "partition exports canonicalize node IDs with str(); collisions are rejected.",
            "compact profile is bounded above 2000 nodes; use full profile for exact path/modularity.",
        ],
    }
    return manifest if full else {
        "schema": manifest["schema"],
        "name": manifest["name"],
        "primary_flow": manifest["primary_flow"],
        "version": manifest["version"],
        "purpose": manifest["purpose"],
        "commands": {key: value for key, value in manifest["commands"].items() if key != "module"},
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
        "input_formats": [item for item in SUPPORTED_INPUT_FORMATS if item != "auto"],
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
        "objective": payload.get("objective"),
        "result": {
            "k": result.get("k"),
            "edge_cut": result.get("edge_cut"),
            "balance_error": result.get("balance_error"),
        },
    }
    schema = payload.get("schema")
    if schema is not None:
        compact["schema"] = schema

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
                "balance_error": c.get("balance_error"),
                "runtime_seconds": c.get("runtime_seconds"),
                "error": c.get("error"),
            }
            for c in candidates
        ]
    return compact


def compact_json(payload: dict) -> str:
    """Encode an AI-facing payload without whitespace overhead."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
