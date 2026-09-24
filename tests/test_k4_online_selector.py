from __future__ import annotations

import json
from pathlib import Path

from experiments.k4_online_selector import SEEDS, _pairwise_medians, _predict_alternate, run


FEATURES = (
    "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    "clustering", "transitivity", "core_number", "diameter",
    "avg_path_length", "modularity",
)


def _fixture(tmp_path: Path) -> Path:
    strategies = [
        "bloc", "bloc-affinity", "metis", "kahip",
        "kaminpar", "kaminpar-strong", "mtkahypar", "mtkahypar-quality",
    ]
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
                        100 + strategy_index
                        - (20 if strategy == oracle else 0)
                        - (5 if seed == 8191 and strategy == strategies[(index + 1) % len(strategies)] else 0)
                    ),
                    "runtime_seconds": 0.01,
                }
            by_seed[seed] = seed_values
        records.append(
            {
                "graph_id": graph_id,
                "corpus": corpus,
                "topology": {
                    name: 0.1 * (index + 1)
                    for name in FEATURES
                },
                "oracle_strategy": oracle,
                "seed_oracles": [oracle] * 5,
                "stable": True,
                "by_seed": by_seed,
            }
        )

    payload = {
        "schema_version": "1.0",
        "commit_sha": "fixture",
        "git_head_sha": "fixture",
        "k": 4,
        "seeds": list(SEEDS),
        "candidate_strategies": strategies,
        "graph_manifest": records,
    }
    path = tmp_path / "k4-five-seed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loader_and_run(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    result = run(path)
    aggregate = result["aggregate"]
    assert aggregate["graphs"] == 20
    assert aggregate["seed_units"] == 100
    assert aggregate["selector"]["graphs"] == 20
    assert result["seeds"] == list(SEEDS)


def test_pairwise_prediction_chooses_negative_training_candidate() -> None:
    strategies = ("s0", "s1", "s2")
    records = []
    for index in range(3):
        records.append(
            {
                "graph_id": f"g{index}",
                "corpus": str(index),
                "topology": {name: float(index + 1) for name in FEATURES},
                "oracle_strategy": "s0",
                "stable": True,
                "seed_oracles": ["s0"] * 5,
                "by_seed": {
                    seed: {
                        "s0": {"edge_cut": 100.0, "runtime_seconds": 0.01},
                        "s1": {"edge_cut": 110.0, "runtime_seconds": 0.01},
                        "s2": {"edge_cut": 80.0, "runtime_seconds": 0.01},
                    }
                    for seed in SEEDS
                },
            }
        )

    from atof.routing import LearnedTopologyRouter

    router = LearnedTopologyRouter(
        features=FEATURES,
        scale_mode="iqr",
        metric="l2",
    ).fit(
        [
            {
                "graph": record["graph_id"],
                "topology": record["topology"],
                "oracle_strategy": record["oracle_strategy"],
            }
            for record in records
        ]
    )
    pair, candidate, rank = _pairwise_medians(records, router)
    candidate_name, prediction = _predict_alternate(
        ("s0", "s1", "s2"),
        pair_median=pair,
        candidate_median=candidate,
        rank_median=rank,
    )
    assert candidate_name == "s2"
    assert prediction < 0.0
