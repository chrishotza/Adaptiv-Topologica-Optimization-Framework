import json
from pathlib import Path

from experiments.online_selector_hierarchical_fusion import LOCAL_KS, RADIUS_THRESHOLDS, run


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
