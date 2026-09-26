from experiments.k8_external_holdout_split import (
    EXTERNAL_DATASETS,
    EXTERNAL_SEEDS,
    ROUTER_CONFIGS,
    TRAINING_SEEDS,
)

def test_external_dataset_registry_is_frozen():
    assert set(EXTERNAL_DATASETS) == {
        "ego_facebook",
        "p2p_gnutella08",
        "ca_astroph",
        "ca_condmat",
    }

def test_external_seed_grid_is_fresh():
    prior = {7, 42, 101, 1337, 1618, 2024, 2718, 3141, 8191, 65537}
    assert not prior.intersection(EXTERNAL_SEEDS)
    assert set(TRAINING_SEEDS).isdisjoint(EXTERNAL_SEEDS)

def test_only_frozen_router_configs_are_evaluated():
    assert set(ROUTER_CONFIGS) == {"all_iqr_l2", "global_paths_iqr_l2"}
