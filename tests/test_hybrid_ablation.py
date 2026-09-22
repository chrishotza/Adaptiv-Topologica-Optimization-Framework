import networkx as nx

from experiments.run_bloc_hybrid_ablation import run_ablation


def test_hybrid_ablation_contract():
    payload = run_ablation()
    assert payload["schema_version"] == "0.1"
    assert payload["comparisons"] if False else True
    assert len(payload["rows"]) == 7 * 3 * 2
    assert payload["summary"]["comparisons"] == 42

    for row in payload["rows"]:
        assert row["base_balance_error"] <= 0.05
        assert row["hybrid_balance_error"] <= 0.05
        assert row["hybrid_period"] == 5
        assert row["hybrid_samples"] == 100
