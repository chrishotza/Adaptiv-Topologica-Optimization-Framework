from experiments.run_external_validation import run_external_validation


def test_external_validation(tmp_path):
    output = tmp_path / "external.json"
    payload = run_external_validation(
        output_path=output,
        seeds=(42,),
        iterations=1,
        bootstrap_resamples=100,
    )

    assert output.exists()
    assert payload["corpus_type"] == "standard_reference_graphs"
    assert len(payload["graphs"]) == 4
    assert len(payload["rows"]) == 28
    assert payload["routing"]["graphs"] == 4
    assert 0.0 <= payload["routing"]["learned_oracle_agreement"] <= 1.0
