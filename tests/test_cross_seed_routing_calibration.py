import json
from pathlib import Path

from experiments.cross_seed_routing_calibration import run


def test_cross_seed_calibration_smoke(tmp_path: Path) -> None:
    strategies = ["s1", "s2"]
    seeds = [42, 101, 2024]
    rows = []
    graph_metadata = {}

    for corpus, graph_name, topology, cuts in [
        ("a", "g1", {"density": 0.1}, {42: [10.0, 8.0], 101: [9.0, 8.0], 2024: [10.0, 8.0]}),
        ("b", "g2", {"density": 0.9}, {42: [7.0, 9.0], 101: [8.0, 9.0], 2024: [7.0, 9.0]}),
        ("c", "g3", {"density": 0.5}, {42: [6.0, 6.0], 101: [5.0, 6.0], 2024: [6.0, 5.0]}),
        ("d", "g4", {"density": 0.7}, {42: [11.0, 10.0], 101: [10.0, 11.0], 2024: [12.0, 10.0]}),
    ]:
        graph_id = f"{corpus}/{graph_name}"
        graph_metadata[graph_id] = {
            "corpus": corpus,
            "topology": topology,
            "nodes": 10,
            "edges": 20,
        }
        for seed, values in cuts.items():
            for strategy, cut in zip(strategies, values):
                rows.append({
                    "graph_id": graph_id,
                    "corpus": corpus,
                    "graph": graph_name,
                    "seed": seed,
                    "strategy": strategy,
                    "edge_cut": cut,
                    "status": "ok",
                })

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

    assert result["aggregate"]["graphs"] == 4
    assert result["aggregate"]["seed_units"] == 12
    assert 0.0 <= result["aggregate"]["fraction_graphs_with_multiple_seed_oracles"] <= 1.0
    assert len(result["folds"]) == 4
