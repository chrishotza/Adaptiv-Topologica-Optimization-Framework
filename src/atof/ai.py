from __future__ import annotations

from . import __version__


def build_ai_manifest(*, full: bool = False) -> dict:
    """Return a compact, stable context contract for AI agents and automation."""
    manifest = {
        "schema": "atof.ai.v1",
        "name": "atof",
        "version": __version__,
        "purpose": "Open-source graph optimization interface: profile, compare, and partition graphs.",
        "primary_flow": "load_graph -> profile -> portfolio/optimizer -> machine-readable result",
        "commands": {
            "profile": "atof profile <graph>",
            "optimize": "atof optimize <graph> --engine portfolio",
            "ai": "atof ai",
            "version": "atof --version",
        },
        "input": {
            "formats": ["edgelist", "graphml", "gexf", "gml"],
            "default_format": "auto",
            "default_seed": 42,
        },
        "portfolio": {
            "k": 2,
            "objective": "minimum unweighted edge cut with balanced two-way partition",
            "backends": [
                "BLOCReloc(baseline)",
                "BLOCReloc(affinity)",
                "NetworkX(Kernighan-Lin)",
                "METIS(PyMetis, optional)",
                "KaHIP(KaFFPa-Strong, optional)",
            ],
            "selection": "empirical minimum edge_cut; ties prefer balance, runtime, name",
        },
        "output": {
            "default": "JSON",
            "compact": "JSON with graph size, strategy, objective metrics, and candidate summary",
            "full": "JSON with topology and selected node-to-block partition",
        },
        "ai_rules": [
            "Prefer --engine portfolio for a practical open-source backend comparison.",
            "Use --compact when full topology or partition mapping is unnecessary.",
            "Treat regime/selection as descriptive evidence, not a universal optimum claim.",
            "Optional backend failures are reported instead of hidden.",
        ],
        "limits": [
            "portfolio mode currently supports k=2",
            "current common objective is unweighted edge cut",
            "weighted/multiway portfolio support is not yet part of the contract",
        ],
    }
    if not full:
        return {
            "schema": manifest["schema"],
            "name": manifest["name"],
            "version": manifest["version"],
            "purpose": manifest["purpose"],
            "commands": manifest["commands"],
            "portfolio": manifest["portfolio"],
            "output": manifest["output"],
            "limits": manifest["limits"],
        }
    return manifest


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
    candidates = payload.get("candidates")
    if candidates is not None:
        compact["candidates"] = [
            {
                "name": c.get("name"),
                "available": c.get("available"),
                "edge_cut": c.get("edge_cut"),
                "runtime_seconds": c.get("runtime_seconds"),
                "error": c.get("error"),
            }
            for c in candidates
        ]
    return compact
