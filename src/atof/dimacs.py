from __future__ import annotations

import bz2
import hashlib
import io
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import networkx as nx


@dataclass(frozen=True)
class DimacsDataset:
    """A DIMACS graph-partitioning/clustering testbed graph."""

    name: str
    source: str
    reference_url: str
    download_url: str
    nodes: int
    edges: int
    description: str
    notes: str = ""

    @property
    def filename(self) -> str:
        return self.download_url.rsplit("/", 1)[-1]


def _parse_metis_graph(payload: bytes) -> nx.Graph:
    with bz2.BZ2File(io.BytesIO(payload), mode="rb") as stream:
        lines = [
            line.decode("utf-8", errors="replace").rstrip("\r\n")
            for line in stream
        ]

    header_index = None
    header = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        header_index = index
        header = stripped.split()
        break

    if header_index is None or header is None:
        raise ValueError("DIMACS graph is empty")

    if len(header) < 2:
        raise ValueError(f"invalid METIS header: {' '.join(header)!r}")

    n = int(header[0])
    fmt = int(header[2]) if len(header) >= 3 else 0
    has_vertex_weights = bool(fmt % 100 >= 10)
    has_edge_weights = bool(fmt % 10 == 1)

    adjacency_lines = []
    for line in lines[header_index + 1 :]:
        if line.lstrip().startswith("%"):
            continue
        adjacency_lines.append(line.strip())
        if len(adjacency_lines) == n:
            break

    if len(adjacency_lines) != n:
        raise ValueError(
            f"expected {n} adjacency lines, got {len(adjacency_lines)}"
        )

    graph = nx.Graph()
    graph.add_nodes_from(range(n))

    for idx, adjacency in enumerate(adjacency_lines):
        tokens = adjacency.split()
        start = 1 if has_vertex_weights else 0
        tokens = tokens[start:]

        if has_edge_weights:
            if len(tokens) % 2:
                raise ValueError(
                    f"odd weighted adjacency token count at vertex {idx + 1}"
                )
            neighbors = tokens[::2]
        else:
            neighbors = tokens

        for token in neighbors:
            neighbor = int(token) - 1
            if neighbor < 0 or neighbor >= n:
                raise ValueError(
                    f"neighbor {neighbor + 1} outside 1..{n} at vertex {idx + 1}"
                )
            if neighbor != idx:
                graph.add_edge(idx, neighbor)

    return nx.convert_node_labels_to_integers(graph, ordering="default")


def parse_dimacs_bytes(payload: bytes) -> nx.Graph:
    """Parse a DIMACS Metis-format bz2 graph into a simple undirected graph."""
    return _parse_metis_graph(payload)


def download_dimacs_dataset(
    dataset: DimacsDataset,
    *,
    cache_dir: str | Path | None = None,
    timeout: float = 120.0,
) -> tuple[nx.Graph, dict]:
    root = (
        Path(cache_dir)
        if cache_dir is not None
        else Path.home() / ".cache" / "atof" / "dimacs"
    )
    root.mkdir(parents=True, exist_ok=True)
    destination = root / dataset.filename

    if destination.exists():
        payload = destination.read_bytes()
        cache_hit = True
    else:
        request = urllib.request.Request(
            dataset.download_url,
            headers={"User-Agent": "ATOF/0.5.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        destination.write_bytes(payload)
        cache_hit = False

    digest = hashlib.sha256(payload).hexdigest()
    graph = parse_dimacs_bytes(payload)

    provenance = {
        "name": dataset.name,
        "source": dataset.source,
        "reference_url": dataset.reference_url,
        "download_url": dataset.download_url,
        "cache_path": str(destination),
        "cache_hit": cache_hit,
        "sha256": digest,
        "bytes": len(payload),
        "declared_nodes": dataset.nodes,
        "declared_edges": dataset.edges,
        "loaded_nodes": graph.number_of_nodes(),
        "loaded_edges": graph.number_of_edges(),
        "format": "DIMACS 10th Implementation Challenge METIS-style graph",
        "normalized_for_atof": "simple undirected graph; self-loops removed",
    }
    return graph, provenance


def dimacs_independent_corpus() -> tuple[DimacsDataset, ...]:
    """Prespecified independent real-world DIMACS clustering testbed subset."""
    base = "https://sites.cc.gatech.edu/dimacs10/archive/data/clustering"
    ref = "https://sites.cc.gatech.edu/dimacs10/archive/clustering.shtml"

    return (
        DimacsDataset(
            name="jazz",
            source="DIMACS 10th Challenge clustering testbed; Gleiser & Danon (2003)",
            reference_url=ref,
            download_url=f"{base}/jazz.graph.bz2",
            nodes=198,
            edges=2742,
            description="Jazz musicians social network.",
        ),
        DimacsDataset(
            name="email_urv",
            source="DIMACS 10th Challenge clustering testbed; Guimera et al. (2003)",
            reference_url=ref,
            download_url=f"{base}/email.graph.bz2",
            nodes=1133,
            edges=5451,
            description="Email-interchange network at Universitat Rovira i Virgili.",
        ),
        DimacsDataset(
            name="pgp_giant",
            source="DIMACS 10th Challenge clustering testbed; Boguna et al. (2004)",
            reference_url=ref,
            download_url=f"{base}/PGPgiantcompo.graph.bz2",
            nodes=10680,
            edges=24316,
            description="Pretty-Good-Privacy users network giant component.",
        ),
        DimacsDataset(
            name="as_22july06",
            source="DIMACS 10th Challenge clustering testbed; Newman / Oregon Route Views",
            reference_url=ref,
            download_url=f"{base}/as-22july06.graph.bz2",
            nodes=22963,
            edges=48436,
            description="Internet autonomous-system network snapshot.",
        ),
        DimacsDataset(
            name="power",
            source="DIMACS 10th Challenge clustering testbed; Watts & Strogatz power grid",
            reference_url=ref,
            download_url=f"{base}/power.graph.bz2",
            nodes=4941,
            edges=6594,
            description="Western States Power Grid topology.",
        ),
        DimacsDataset(
            name="astro_ph",
            source="DIMACS 10th Challenge clustering testbed; Newman astrophysics collaborations",
            reference_url=ref,
            download_url=f"{base}/astro-ph.graph.bz2",
            nodes=16706,
            edges=121251,
            description="Astrophysics coauthorship network.",
        ),
    )
