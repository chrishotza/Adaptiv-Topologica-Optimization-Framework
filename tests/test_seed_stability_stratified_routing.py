import json
from pathlib import Path

from experiments.seed_stability_stratified_routing import run


def test_seed_stability_stratification_smoke(tmp_path: Path) -> None:
    strategies = [f"s{i}" for i in range(11)]
    seeds = [42, 101, 2024]
    rows = []
    graph_metadata = {}

    for index in range(20):
        corpus = ("a", "b", "c", "d")[index // 5]
        graph_id = f"{corpus}/g{index:02d}"
        graph_metadata[graph_id] = {
            "corpus": corpus,
            "topology": {"density": 0.05 + index / 25.0},
        }
        for seed_index, seed in enumerate(seeds):
            oracle = strategies[index % len(strategies)]
            if index % 4 == 0 and seed_index == 2:
                oracle = strategies[(index + 1) % len(strategies)]
            for strategy_index, strategy in enumerate(strategies):
                cut = 100.0 + strategy_index
                if strategy == oracle:
                    cut -= 10.0
                rows.append({
                    "graph_id": graph_id,
                    "corpus": corpus,
                    "seed": seed,
                    "strategy": strategy,
                    "edge_cut": cut,
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

    assert result["aggregate"]["graphs"] == 20
    assert result["aggregate"]["stable_graphs"] + result["aggregate"]["unstable_graphs"] == 20
    assert len(result["folds"]) == 4
    assert result["aggregate"]["paired_better_graphs"] + result["aggregate"]["paired_worse_graphs"] + result["aggregate"]["paired_ties"] == 20
