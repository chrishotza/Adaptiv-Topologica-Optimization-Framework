from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import networkx as nx

from atof.dimacs import download_dimacs_dataset, dimacs_independent_corpus
from atof.snap import download_snap_dataset, snap_scalability_corpus
from atof.topology import TopologyProfiler


def _datasets():
    dimacs = {item.name: item for item in dimacs_independent_corpus()}
    snap = {item.name: item for item in snap_scalability_corpus()}
    return {
        "as_22july06": ("dimacs", dimacs["as_22july06"]),
        "astro_ph": ("dimacs", dimacs["astro_ph"]),
        "wiki_vote": ("snap", snap["wiki_vote"]),
    }


def validate(
    fixture_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    expected = json.loads(Path(fixture_path).read_text(encoding="utf-8"))["graphs"]
    results = {}
    for name, (kind, dataset) in _datasets().items():
        started = time.perf_counter()
        if kind == "dimacs":
            graph, _ = download_dimacs_dataset(dataset, cache_dir=cache_dir)
        else:
            graph, _ = download_snap_dataset(dataset, cache_dir=cache_dir)

        observed = TopologyProfiler().profile(graph).to_dict()
        reference = expected[name]

        numeric_keys = [
            "density",
            "avg_degree",
            "degree_std",
            "hub_ratio",
            "degree_gini",
            "clustering",
            "transitivity",
            "assortativity",
            "core_number",
            "diameter",
            "avg_path_length",
            "modularity",
        ]
        exact_keys = [
            "node_count",
            "edge_count",
            "max_degree",
            "communities",
        ]

        for key in exact_keys:
            assert observed[key] == reference[key], (name, key, observed[key], reference[key])
        for key in numeric_keys:
            assert abs(observed[key] - reference[key]) <= 1e-9 * max(1.0, abs(reference[key])), (
                name,
                key,
                observed[key],
                reference[key],
            )

        results[name] = {
            "runtime_seconds": time.perf_counter() - started,
            "topology": observed,
        }

    return {
        "graphs": results,
        "validated_graph_count": len(results),
        "method": "exact topology values compared against frozen 26-graph benchmark state",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = validate(args.fixture)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
