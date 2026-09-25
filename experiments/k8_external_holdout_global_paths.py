from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import platform
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

from atof.routing import FEATURE_GROUPS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci
from experiments.k8_degree_hub_replication import _graph_record
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora

K = 8
TRAINING_SEEDS = (42, 101, 2024)
EXTERNAL_SEEDS = (5003, 7003, 9001, 12011, 16001)
RESAMPLES = 5000
BOOTSTRAP_SEED = 2024

ROUTER_CONFIGS = {
    "all_iqr_l2": tuple(FEATURE_GROUPS["all"]),
    "global_paths_iqr_l2": tuple(FEATURE_GROUPS["global_paths"]),
}

EXTERNAL_DATASETS = (
    {
        "name": "ego_facebook",
        "source": "McAuley & Leskovec (2012), SNAP",
        "reference_url": "https://snap.stanford.edu/data/ego-Facebook.html",
        "download_url": "https://snap.stanford.edu/data/facebook_combined.txt.gz",
        "directed": False,
        "declared_nodes": 4039,
        "declared_edges": 88234,
    },
    {
        "name": "p2p_gnutella08",
        "source": "Ripeanu, Foster & Iamnitchi; Leskovec et al., SNAP",
        "reference_url": "https://snap.stanford.edu/data/p2p-Gnutella08.html",
        "download_url": "https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz",
        "directed": True,
        "declared_nodes": 6301,
        "declared_edges": 20777,
    },
    {
        "name": "ca_astroph",
        "source": "SNAP Arxiv Astro Physics collaboration network",
        "reference_url": "https://snap.stanford.edu/data/ca-AstroPh.html",
        "download_url": "https://snap.stanford.edu/data/ca-AstroPh.txt.gz",
        "directed": False,
        "declared_nodes": 18772,
        "declared_edges": 198110,
    },
    {
        "name": "ca_condmat",
        "source": "SNAP Arxiv Condensed Matter collaboration network",
        "reference_url": "https://snap.stanford.edu/data/ca-CondMat.html",
        "download_url": "https://snap.stanford.edu/data/ca-CondMat.txt.gz",
        "directed": False,
        "declared_nodes": 23133,
        "declared_edges": 93497,
    },
)


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _download_graph(spec: dict, cache_dir: Path) -> tuple[nx.Graph, dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = spec["download_url"].rsplit("/", 1)[-1]
    destination = cache_dir / filename

    if destination.exists():
        payload = destination.read_bytes()
        cache_hit = True
    else:
        request = urllib.request.Request(
            spec["download_url"],
            headers={"User-Agent": "ATOF/0.6.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        destination.write_bytes(payload)
        cache_hit = False

    digest = hashlib.sha256(payload).hexdigest()
    graph = nx.Graph()

    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        for raw in io.TextIOWrapper(stream, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            graph.add_edge(parts[0], parts[1])

    if spec["directed"]:
        graph = graph.to_undirected()
    graph.remove_edges_from(nx.selfloop_edges(graph))
    graph = nx.convert_node_labels_to_integers(graph, ordering="default")

    provenance = {
        "name": spec["name"],
        "source": spec["source"],
        "reference_url": spec["reference_url"],
        "download_url": spec["download_url"],
        "cache_path": str(destination),
        "cache_hit": cache_hit,
        "sha256": digest,
        "bytes": len(payload),
        "declared_nodes": spec["declared_nodes"],
        "declared_edges": spec["declared_edges"],
        "loaded_nodes": graph.number_of_nodes(),
        "loaded_edges": graph.number_of_edges(),
        "directed_source": spec["directed"],
        "normalized_for_atof": "simple undirected graph with self-loops removed",
    }
    return graph, provenance


def _fit(training_records: list[dict], features: tuple[str, ...]) -> LearnedTopologyRouter:
    rows = [
        {
            "graph": record["graph_id"],
            "topology": record["topology"],
            "oracle_strategy": record["oracle_strategy"],
        }
        for record in training_records
    ]
    return LearnedTopologyRouter(
        features=features,
        scale_mode="iqr",
        metric="l2",
    ).fit(rows)


def _regret(record: dict, strategy: str) -> float:
    oracle_cut = float(record["strategy_means"][record["oracle_strategy"]])
    selected_cut = float(record["strategy_means"][strategy])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0


def _summary(values: list[float]) -> dict:
    low, high = bootstrap_mean_ci(
        values,
        resamples=RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "graphs": len(values),
        "mean_relative_regret": _mean(values),
        "bootstrap_95_ci": [low, high],
    }


def _evaluate_predictions(records: list[dict], predictions: dict[str, str]) -> dict:
    graph_values = {
        record["graph_id"]: _regret(record, predictions[record["graph_id"]])
        for record in records
    }
    return {
        **_summary(list(graph_values.values())),
        "graph_values": graph_values,
        "decisions": {
            record["graph_id"]: predictions[record["graph_id"]]
            for record in records
        },
    }


def run(output_path: str | Path, cache_dir: str | Path | None = None) -> dict:
    started = time.perf_counter()
    cache_root = Path(cache_dir or ".cache/snap_external")

    corpora, provenance = _load_expanded_corpora(cache_dir=cache_root / "training")
    training_records = [
        _graph_record(graph, corpus, name, seeds=TRAINING_SEEDS)
        for corpus, graphs in sorted(corpora.items())
        for name, graph in sorted(graphs.items())
    ]

    if len(training_records) != 20:
        raise AssertionError("expected exactly 20 training graphs")

    external_graphs: dict[str, nx.Graph] = {}
    external_provenance: dict[str, dict] = {}
    for spec in EXTERNAL_DATASETS:
        graph, metadata = _download_graph(spec, cache_root / "external")
        external_graphs[spec["name"]] = graph
        external_provenance[spec["name"]] = metadata

    if len(external_graphs) != 4:
        raise AssertionError("expected exactly 4 external holdout graphs")

    training_names = {record["graph_id"] for record in training_records}
    if training_names.intersection(external_graphs):
        raise AssertionError("external holdout graph overlaps training corpus")

    external_records = [
        _graph_record(
            graph,
            "external_holdout",
            name,
            seeds=EXTERNAL_SEEDS,
        )
        for name, graph in sorted(external_graphs.items())
    ]

    if any(
        seed in set(TRAINING_SEEDS) | {7, 8191, 1337, 1618, 2718, 3141, 65537}
        for seed in EXTERNAL_SEEDS
    ):
        raise AssertionError("external seed grid overlaps prior k=8 routing seeds")

    if any(len(record["seed_oracles"]) != len(EXTERNAL_SEEDS) for record in external_records):
        raise AssertionError("external seed grid incomplete")

    routers = {}
    for name, features in ROUTER_CONFIGS.items():
        router = _fit(training_records, features)
        predictions = {
            record["graph_id"]: router.predict(record["topology"])
            for record in external_records
        }
        routers[name] = _evaluate_predictions(external_records, predictions)

    oracle_counts = Counter(record["oracle_strategy"] for record in training_records)
    majority_strategy = min(
        oracle_counts,
        key=lambda strategy: (-oracle_counts[strategy], strategy),
    )
    majority = _evaluate_predictions(
        external_records,
        {record["graph_id"]: majority_strategy for record in external_records},
    )

    paired = {}
    for router_name in ("all_iqr_l2", "global_paths_iqr_l2"):
        paired_values = [
            routers[router_name]["graph_values"][record["graph_id"]]
            - majority["graph_values"][record["graph_id"]]
            for record in external_records
        ]
        paired_low, paired_high = bootstrap_mean_ci(
            paired_values,
            resamples=RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
        paired[router_name] = {
            "mean_router_minus_majority": _mean(paired_values),
            "bootstrap_95_ci": [paired_low, paired_high],
            "router_better_graphs": sum(value < 0 for value in paired_values),
            "router_worse_graphs": sum(value > 0 for value in paired_values),
            "ties": sum(value == 0 for value in paired_values),
            "graph_values": {
                record["graph_id"]: value
                for record, value in zip(external_records, paired_values)
            },
        }

    result = {
        "schema_version": "1.0",
        "protocol": "k=8 external graph holdout with frozen routing configurations",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": K,
        "training_seeds": list(TRAINING_SEEDS),
        "external_seeds": list(EXTERNAL_SEEDS),
        "training_graphs": len(training_records),
        "external_graphs": len(external_records),
        "training_corpora": sorted({record["corpus"] for record in training_records}),
        "external_dataset_provenance": external_provenance,
        "candidate_strategies": list(
            training_records[0]["strategy_means"].keys()
        ),
        "routers": routers,
        "majority_control": {
            "strategy": majority_strategy,
            **majority,
        },
        "paired_vs_majority": paired,
        "external_manifest": external_records,
        "evidence_boundary": [
            "Router configurations were frozen before generating the external solver outcomes.",
            "The four holdout graphs were not present in the 20-graph training corpus.",
            "The external solver seed grid was not used in prior k=8 routing experiments.",
            "Training feature scaling and oracle labels use only the 20 training graphs.",
            "The held-out oracle is used only to evaluate external predictions.",
            "This is external graph-domain validation; it does not alter production/default routing behavior.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "majority": majority["mean_relative_regret"],
                "all_iqr_l2": routers["all_iqr_l2"]["mean_relative_regret"],
                "global_paths_iqr_l2": routers["global_paths_iqr_l2"]["mean_relative_regret"],
                "paired_vs_majority": paired,
            },
            indent=2,
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    run(args.output, args.cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
