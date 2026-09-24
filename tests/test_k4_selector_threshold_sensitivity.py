from __future__ import annotations

import json
from pathlib import Path

from experiments.k4_online_selector import SEEDS
from experiments.k4_selector_threshold_sensitivity import run


def _fixture(tmp_path: Path) -> Path:
    strategies = [
        "bloc",
        "bloc-affinity",
        "metis",
        "kahip",
        "kaminpar",
        "kaminpar-strong",
        "mtkahypar",
        "mtkahypar-quality",
    ]
    features = (
        "density",
        "avg_degree",
        "degree_std",
        "hub_ratio",
        "degree_gini",
        "clustering",
        "transitivity",
        "core_number",
        "diameter",
        "avg_path_length",
        "modularity",
    )

    records = []
    for index in range(20):
        corpus = ("a", "b", "c", "d")[index // 5]
        graph_id = f"{corpus}/g{index:02d}"
        oracle = strategies[index % len(strategies)]
        by_seed = {}

        for seed in SEEDS:
            seed_values = {}
            for strategy_index, strategy in enumerate(strategies):
                seed_values[strategy] = {
                    "edge_cut": float(
                        100
                        + strategy_index
                        - (20 if strategy == oracle else 0)
                    ),
                    "runtime_seconds": 0.01 + 0.001 * strategy_index,
                }
            by_seed[seed] = seed_values

        records.append(
            {
                "graph_id": graph_id,
                "corpus": corpus,
                "topology": {
                    feature: 0.1 * (index + 1)
                    for feature in features
                },
                "oracle_strategy": oracle,
                "seed_oracles": [oracle] * 5,
                "stable": True,
                "by_seed": by_seed,
            }
        )

    payload = {
        "schema_version": "1.0",
        "benchmark_commit": "fixture",
        "benchmark_head": "fixture",
        "k": 4,
        "seeds": list(SEEDS),
        "candidate_strategies": strategies,
        "graph_manifest": records,
    }
    path = tmp_path / "k4-five-seed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_threshold_sensitivity_manifest(tmp_path: Path) -> None:
    result = run(_fixture(tmp_path))

    assert result["k"] == 4
    assert result["seeds"] == list(SEEDS)
    assert result["thresholds"] == [0.0, 0.0025, 0.005, 0.01, 0.02]
    assert len(result["cells"]) == 5

    for cell in result["cells"]:
        assert cell["selector"]["graphs"] == 20
        assert cell["top1"]["graphs"] == 20
        assert 0.0 <= cell["probe_rate"] <= 1.0
        assert 1.0 <= cell["mean_actions"] <= 2.0
        assert len(cell["paired_selector_minus_top1"]["bootstrap_95_ci"]) == 2
