from experiments.k8_hybrid_representation_confirmatory import (
    HYBRID_FEATURES,
    ROUTER_CONFIGS,
    SEEDS,
)


def test_hybrid_feature_config_is_frozen_union():
    assert ROUTER_CONFIGS["degree_hub_global_paths_iqr_l2"] == HYBRID_FEATURES
    assert set(HYBRID_FEATURES) == {
        "density",
        "avg_degree",
        "degree_std",
        "hub_ratio",
        "degree_gini",
        "core_number",
        "diameter",
        "avg_path_length",
    }


def test_fresh_seed_grid_has_no_prior_k8_seed_overlap():
    prior = {7, 42, 101, 1337, 1618, 2024, 2718, 3141, 8191, 65537}
    assert len(SEEDS) == 5
    assert not prior.intersection(SEEDS)
