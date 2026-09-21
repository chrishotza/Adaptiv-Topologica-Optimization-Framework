from experiments.run_statistical_analysis import run_statistical_analysis


def test_statistical_analysis(tmp_path):
    output = tmp_path / "stats.json"
    payload = run_statistical_analysis(
        output_path=output,
        k=2,
        seeds=(42,),
        iterations=2,
        resamples=100,
    )

    assert output.exists()
    assert payload["protocol"] == "graph-level paired bootstrap"
    assert len(payload["comparisons"]) == 4
    assert all(item["n_graphs"] == 7 for item in payload["comparisons"])
