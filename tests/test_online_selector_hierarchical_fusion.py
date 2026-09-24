import json
from pathlib import Path

from experiments.online_selector_hierarchical_fusion import (
    LOCAL_KS,
    RADIUS_THRESHOLDS,
    _fused_prediction,
    run,
)


def test_fused_prediction_preserves_candidate_specific_global_priors() -> None:
    global_candidates = [
        {"rank": 1, "candidate": "s1", "prediction": 0.20},
        {"rank": 2, "candidate": "s2", "prediction": -0.10},
    ]
    local = [
        {
            "rank": 1,
            "candidate": "s1",
            "prediction": 0.01,
            "radius": 1.0,
            "support": 3,
            "neighbor_ids": ["a", "b", "c"],
        },
        {
            "rank": 2,
            "candidate": "s2",
            "prediction": 0.02,
            "radius": 1.0,
            "support": 3,
            "neighbor_ids": ["d", "e", "f"],
        },
    ]
    candidate, prediction, meta = _fused_prediction(
        global_candidates,
        local,
        radius_threshold=10.0,
        orientation="global_near",
    )
    assert candidate == "s2"
    assert prediction == -0.10
    assert meta["global_candidate_predictions"]["s1"] == 0.20
    assert meta["global_candidate_predictions"]["s2"] == -0.10


def test_fused_prediction_keeps_global_fallback_for_missing_local_support() -> None:
    global_candidates = [
        {"rank": 1, "candidate": "s1", "prediction": 0.10},
        {"rank": 2, "candidate": "s2", "prediction": -0.20},
    ]
    local = [
        {
            "rank": 1,
            "candidate": "s1",
            "prediction": 0.01,
            "radius": 10.0,
            "support": 3,
            "neighbor_ids": ["a", "b", "c"],
        },
        {
            "rank": 2,
            "candidate": "s2",
            "prediction": None,
            "radius": None,
            "support": 0,
            "neighbor_ids": [],
        },
    ]
    candidate, prediction, meta = _fused_prediction(
        global_candidates,
        local,
        radius_threshold=5.0,
        orientation="global_near",
    )
    assert candidate == "s2"
    assert prediction == -0.20
    assert meta["source"] == "global"


def test_online_selector_hierarchical_fusion_smoke(tmp_path: Path) -> None:
    strategies = [f"s{i}" for i in range(11)]
    seeds = [42, 101, 2024]
    feature_names = [
        "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
        "clustering", "transitivity", "core_number", "diameter",
        "avg_path_length", "modularity",
    ]
    rows = []
    graph_metadata = {}
    for index in range(20):
        corpus = ("a", "b", "c", "d")[index // 5]
        graph_id = f"{corpus}/g{index:02d}"
        graph_metadata[graph_id] = {
            "corpus": corpus,
            "topology": {name: 0.1 * (index + 1) for name in feature_names},
        }
        for seed in seeds:
            oracle = strategies[index % len(strategies)]
            for strategy_index, strategy in enumerate(strategies):
                rows.append({
                    "graph_id": graph_id,
                    "corpus": corpus,
                    "seed": seed,
                    "strategy": strategy,
                    "edge_cut": 100.0 + strategy_index - (20.0 if strategy == oracle else 0.0),
                    "runtime_seconds": 0.01 + 0.001 * strategy_index,
                    "status": "ok",
                })
    payload = {
        "schema_version": "1.0",
        "commit_sha": "fixture",
        "matched_graphs": 20,
        "candidate_strategies": strategies,
        "seeds": seeds,
        "rows": rows,
        "graph_metadata": graph_metadata,
    }
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = run(path)
    assert len(result["cells"]) == 2 * len(LOCAL_KS) * len(RADIUS_THRESHOLDS)
    assert all(cell["graphs"] == 20 for cell in result["cells"])
    assert all(cell["selector"]["mean_actions"] <= 2.0 for cell in result["cells"])
