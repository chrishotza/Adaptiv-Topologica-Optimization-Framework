from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib import metadata
from typing import Any

import networkx as nx


def graph_fingerprint(graph: nx.Graph) -> str:
    """Return a stable SHA-256 fingerprint for the current unweighted graph."""
    nodes = sorted((type(node).__name__, repr(node)) for node in graph.nodes())
    edges = []
    for left, right in graph.edges():
        a = (type(left).__name__, repr(left))
        b = (type(right).__name__, repr(right))
        edges.append(tuple(sorted((a, b))))
    payload = {
        "nodes": nodes,
        "edges": sorted(edges),
        "directed": bool(graph.is_directed()),
        "multigraph": bool(graph.is_multigraph()),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def package_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def runtime_metadata() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
    }
