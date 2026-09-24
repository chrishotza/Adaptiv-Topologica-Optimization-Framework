import experiments.fresh_sota_protocol as fresh_sota_protocol
import json
from pathlib import Path

from experiments.online_selector_five_seed_replication import (
    SEEDS,
    _seed_stability,
)
from experiments.topk_routing_coverage import _build_records, _load


def _fixture(tmp_path: Path) -> Path:
    strategies = [f"s{i}" for i in range(11)]
    rows = []
    metadata = {}
    for index in range(20):
        corpus = ("a", "b", "c", "d")[index // 5]
        graph_id = f"{corpus}/g{index:02d}"
        metadata[graph_id] = {
            "corpus": corpus,
            "topology": {"density": 0.1 + index},
        }
        for seed in SEEDS:
            oracle = strategies[(index + (seed == 8191)) % len(strategies)]
            for strategy_index, strategy in enumerate(strategies):
                rows.append(
                    {
                        "graph_id": graph_id,
                        "corpus": corpus,
                        "seed": seed,
                        "strategy": strategy,
                        "edge_cut": (
                            100.0
                            + strategy_index
                            - (20.0 if strategy == oracle else 0.0)
                        ),
                        "runtime_seconds": 0.01,
                        "status": "ok",
                    }
                )
    payload = {
        "schema_version": "1.0",
        "commit_sha": "fixture",
        "matched_graphs": 20,
        "candidate_strategies": strategies,
        "seeds": list(SEEDS),
        "rows": rows,
        "graph_metadata": metadata,
    }
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loader_accepts_five_seed_grid(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    payload, rows = _load(path)
    assert payload["seeds"] == list(SEEDS)
    assert len(rows) == 20 * 11 * 5


def test_worker_honors_explicit_seed_manifest(monkeypatch) -> None:
    import networkx as nx

    graph = nx.path_graph(4)
    seen = []

    monkeypatch.setattr(
        fresh_sota_protocol,
        "_load_expanded_corpora",
        lambda cache_dir=None: (
            {"fixture": {"g": graph}},
            {"fixture": {"type": "unit-test"}},
        ),
    )
    monkeypatch.setattr(
        fresh_sota_protocol,
        "run_strategy",
        lambda strategy, graph, *, seed, k: (
            seen.append((strategy, seed, k))
            or {
                "edge_cut": 1,
                "balance_error": 0.0,
                "runtime_seconds": 0.001,
            }
        ),
    )

    rows = fresh_sota_protocol.run_isolated_strategy(
        "metis",
        cache_dir=None,
        seeds=(7, 8191),
    )

    assert [row["seed"] for row in rows] == [7, 8191]
    assert seen == [("metis", 7, 2), ("metis", 8191, 2)]


def test_seed_stability_flags_changed_oracles(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    payload, rows = _load(path)
    records = _build_records(payload, rows)
    summary = _seed_stability(records)
    assert summary["graphs"] == 20
    assert summary["unstable_graphs"] == 20
    assert summary["unstable_graph_rate"] == 1.0
