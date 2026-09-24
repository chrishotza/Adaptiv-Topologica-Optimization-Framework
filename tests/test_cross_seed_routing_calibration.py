import json
from pathlib import Path

from experiments.cross_seed_routing_calibration import run


def test_cross_seed_calibration_smoke(tmp_path: Path) -> None:
    strategies = [f"s{i}" for i in range(11)]
    seeds = [42, 101, 2024]
    rows = []
    graph_metadata = {}

    for index in range(20):
        corpus = ("a", "b", "c", "d")[index // 5]
        graph_name = f"g{index:02d}"
        graph_id = f"{corpus}/{graph_name}"
        graph_metadata[graph_id] = {
            "corpus": corpus,
            "topology": {"density": 0.05 + index / 25.0},
            "nodes": 10 + index,
            "edges": 20 + index,
        }
        graph_oracle = strategies[index % len(strategies)]
        for seed_index, seed in enumerate(seeds):
            seed_oracle = graph_oracle
            if index % 5 == 0 and seed_index == 2:
                seed_oracle = strategies[(index + 1) % len(strategies)]
            for strategy_index, strategy in enumerate(strategies):
                cut = 100.0 + strategy_index
                if strategy == seed_oracle:
                    cut -= 10.0
                rows.append(
                    {
                        "graph_id": graph_id,
                        "corpus": corpus,
                        "graph": graph_name,
                        "seed": seed,
                        "strategy": strategy,
                        "edge_cut": cut,
                        "status": "ok",
                    }
                )

    payload = {
        "schema_version": "1.0",
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
    assert result["aggregate"]["seed_units"] == 60
    assert 0.0 <= result["aggregate"]["fraction_graphs_with_multiple_seed_oracles"] <= 1.0
    assert len(result["folds"]) == 4
    for fold in result["folds"]:
        assert fold["test_graphs"] == 5
        assert fold["seed_units"] == 15
