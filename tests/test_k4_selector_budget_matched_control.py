from __future__ import annotations

from pathlib import Path

from experiments.k4_online_selector import SEEDS
from experiments.k4_selector_budget_matched_control import run


def _write_fixture(path: Path) -> None:
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
            by_seed[seed] = {
                strategy: {
                    "edge_cut": float(
                        100
                        + strategy_index
                        - (20 if strategy == oracle else 0)
                    ),
                    "runtime_seconds": 0.01,
                }
                for strategy_index, strategy in enumerate(strategies)
            }

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

    import json

    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "benchmark_commit": "fixture",
                "benchmark_head": "fixture",
                "k": 4,
                "seeds": list(SEEDS),
                "candidate_strategies": strategies,
                "graph_manifest": records,
            }
        ),
        encoding="utf-8",
    )


def test_budget_matched_control_contract(tmp_path: Path) -> None:
    path = tmp_path / "benchmark.json"
    _write_fixture(path)

    result = run(path)

    assert result["k"] == 4
    assert result["graphs"] == 20
    assert result["seed_units"] == 100
    assert result["random_control"]["repeats"] == 500
    assert result["selector"]["probe_graph_count"] == 0
    assert result["selector"]["mean_actions"] == 1.0
    assert len(result["selector_minus_random_control"]["bootstrap_95_ci"]) == 2
