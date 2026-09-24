import json

from experiments.k8_degree_hub_replication import FEATURES, K, SEEDS, STRATEGIES, run


def test_k8_degree_hub_protocol_is_frozen() -> None:
    assert K == 8
    assert SEEDS == (7, 42, 101, 2024, 8191)
    assert FEATURES == (
        "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    )
    assert len(STRATEGIES) == 8
    assert "networkx-kl" not in STRATEGIES


def test_manifest_contract(tmp_path):
    assert FEATURES == (
        "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    )
