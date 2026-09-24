from experiments.k4_routing_generalization import FEATURES, K, SEEDS, STRATEGIES


def test_k4_protocol_manifest_is_frozen() -> None:
    assert K == 4
    assert SEEDS == (42, 101, 2024)
    assert len(STRATEGIES) == 8
    assert "networkx-kl" not in STRATEGIES
    assert STRATEGIES == (
        "bloc", "bloc-affinity", "metis", "kahip",
        "kaminpar", "kaminpar-strong", "mtkahypar", "mtkahypar-quality",
    )
    assert len(FEATURES) == 11
    assert "modularity" in FEATURES
