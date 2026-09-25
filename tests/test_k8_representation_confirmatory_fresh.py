from experiments.k8_representation_confirmatory_fresh import ROUTER_CONFIGS, SEEDS

def test_frozen_fresh_seed_grid():
    assert SEEDS == (1337, 2718, 3141, 1618, 65537)
    assert len(set(SEEDS)) == 5

def test_only_two_confirmatory_router_configs():
    assert tuple(ROUTER_CONFIGS) == ("all_iqr_l2", "degree_hub_iqr_l2")
