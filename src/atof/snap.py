from __future__ import annotations

import gzip
import hashlib
import io
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import networkx as nx


@dataclass(frozen=True)
class SnapDataset:
    """A public SNAP edge-list dataset with explicit provenance."""

    name: str
    source: str
    reference_url: str
    download_url: str
    directed: bool
    nodes: int | None
    edges: int | None
    description: str
    notes: str = ""

    @property
    def filename(self) -> str:
        return self.download_url.rsplit("/", 1)[-1]


def _read_snap_bytes(payload: bytes, *, directed: bool) -> nx.Graph:
    graph: nx.Graph
    graph = nx.DiGraph() if directed else nx.Graph()

    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        text = io.TextIOWrapper(stream, encoding="utf-8", errors="replace")
        for raw in text:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            graph.add_edge(parts[0], parts[1])

    if directed:
        graph = graph.to_undirected()
    graph.remove_edges_from(nx.selfloop_edges(graph))
    return nx.convert_node_labels_to_integers(graph, ordering="default")


def parse_snap_bytes(payload: bytes, *, directed: bool = False) -> nx.Graph:
    """Parse a gzipped SNAP edge list into a simple undirected graph for ATOF."""
    return _read_snap_bytes(payload, directed=directed)


def download_snap_dataset(
    dataset: SnapDataset,
    *,
    cache_dir: str | Path | None = None,
    timeout: float = 60.0,
) -> tuple[nx.Graph, dict]:
    """Download/cache a SNAP dataset and return graph plus provenance."""
    root = (
        Path(cache_dir)
        if cache_dir is not None
        else Path.home() / ".cache" / "atof" / "snap"
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
    graph = parse_snap_bytes(payload, directed=dataset.directed)

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
        "directed_source": dataset.directed,
        "normalized_for_atof": "simple undirected graph with self-loops removed",
    }
    return graph, provenance


def snap_reference_corpus() -> tuple[SnapDataset, ...]:
    """Return a moderate-size empirical SNAP corpus suitable for routine validation."""
    return (
        SnapDataset(
            name="c_elegans_frontal",
            source="Kaiser & Hilgetag (2006), SNAP",
            reference_url="https://snap.stanford.edu/data/C-elegans-frontal.html",
            download_url="https://snap.stanford.edu/data/C-elegans-frontal.txt.gz",
            directed=True,
            nodes=131,
            edges=764,
            description="Frontal neuronal connections in C. elegans.",
            notes="Direction is normalized to an undirected structure for the current partitioning objective.",
        ),
        SnapDataset(
            name="florida_bay",
            source="Ulanowicz, Bondavalli & Egnotovich (1997), SNAP",
            reference_url="https://snap.stanford.edu/data/Florida-bay.html",
            download_url="https://snap.stanford.edu/data/Florida-bay.txt.gz",
            directed=True,
            nodes=128,
            edges=2106,
            description="Florida Bay food-web carbon exchange network.",
            notes="Direction is normalized to an undirected structure for the current partitioning objective.",
        ),
        SnapDataset(
            name="s_cerevisiae",
            source="Milo et al. (2002), SNAP",
            reference_url="https://snap.stanford.edu/data/S-cerevisiae.html",
            download_url="https://snap.stanford.edu/data/S-cerevisiae.txt.gz",
            directed=True,
            nodes=690,
            edges=1094,
            description="S. cerevisiae transcriptional regulation network.",
            notes="Signed edge semantics are not used; the current benchmark retains only connectivity.",
        ),
        SnapDataset(
            name="email_eu_core",
            source="Leskovec et al.; Yin et al., SNAP",
            reference_url="https://snap.stanford.edu/data/email-Eu-core.html",
            download_url="https://snap.stanford.edu/data/email-Eu-core.txt.gz",
            directed=True,
            nodes=1005,
            edges=25571,
            description="Email communication network within a European research institution.",
            notes="Department labels are not used by the benchmark.",
        ),
    )


def snap_scalability_corpus() -> tuple[SnapDataset, ...]:
    """Return larger SNAP graphs for optional scalability/generalization studies."""
    return (
        SnapDataset(
            name="ca_grqc",
            source="SNAP Arxiv High Energy Physics collaboration network",
            reference_url="https://snap.stanford.edu/data/ca-GrQc.html",
            download_url="https://snap.stanford.edu/data/ca-GrQc.txt.gz",
            directed=False,
            nodes=5242,
            edges=14496,
            description="Arxiv General Relativity and Quantum Cosmology collaboration network.",
        ),
        SnapDataset(
            name="ca_hepth",
            source="SNAP Arxiv High Energy Physics Theory collaboration network",
            reference_url="https://snap.stanford.edu/data/ca-HepTh.html",
            download_url="https://snap.stanford.edu/data/ca-HepTh.txt.gz",
            directed=False,
            nodes=9877,
            edges=25998,
            description="Arxiv High Energy Physics Theory collaboration network.",
        ),
        SnapDataset(
            name="wiki_vote",
            source="Leskovec, Huttenlocher & Kleinberg, SNAP",
            reference_url="https://snap.stanford.edu/data/wiki-Vote.html",
            download_url="https://snap.stanford.edu/data/wiki-Vote.txt.gz",
            directed=True,
            nodes=7115,
            edges=103689,
            description="Wikipedia adminship vote network.",
            notes="Vote direction is normalized to undirected connectivity; vote semantics are not used.",
        ),
    )
