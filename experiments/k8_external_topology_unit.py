from __future__ import annotations

import argparse
import gzip
import io
import json
import urllib.request
from pathlib import Path

import networkx as nx

from atof.topology import TopologyProfiler

DATASETS = {
    "ca_astroph": "https://snap.stanford.edu/data/ca-AstroPh.txt.gz",
    "ca_condmat": "https://snap.stanford.edu/data/ca-CondMat.txt.gz",
}


def load_external_graph(dataset: str, cache_dir: Path) -> nx.Graph:
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = DATASETS[dataset]
    destination = cache_dir / url.rsplit("/", 1)[-1]
    if destination.exists():
        payload = destination.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "ATOF/0.6.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        destination.write_bytes(payload)

    graph = nx.Graph()
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        for raw in io.TextIOWrapper(stream, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                graph.add_edge(parts[0], parts[1])
    graph.remove_edges_from(nx.selfloop_edges(graph))
    return nx.convert_node_labels_to_integers(graph, ordering="default")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()

    graph = load_external_graph(args.dataset, args.cache_dir)
    topology = TopologyProfiler().profile(graph).to_dict()
    payload = {
        "schema_version": "1.0",
        "dataset": args.dataset,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "topology": topology,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "dataset": args.dataset,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
