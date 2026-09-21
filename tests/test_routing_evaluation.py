from experiments.run_routing_evaluation import run_routing_evaluation


def test_routing_evaluation_graph_level(tmp_path):
    output = tmp_path / "routing.json"
    payload = run_routing_evaluation(
        output_path=output,
        k=2,
        seeds=(42,),
        iterations=2,
    )

    assert output.exists()
    assert payload["protocol"] == "leave-one-graph-out"
    assert payload["summary"]["graphs"] == 7
    assert all(row["training_graphs"] == 6 for row in payload["folds"])
    assert all("oracle_strategy" in row for row in payload["folds"])
    assert "spectral_bisection" in payload["candidate_strategies"]
