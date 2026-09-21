from experiments.run_metis_validation import STRATEGY
from experiments.run_router_confirmatory import LOCKED_CONFIGS


def test_metis_confirmatory_strategy_is_additive():
    assert STRATEGY == "metis_multilevel_balanced"
    assert len(LOCKED_CONFIGS) == 3


def test_metis_does_not_change_locked_router_configurations():
    assert LOCKED_CONFIGS["all_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_minmax_l2"][1:] == ("minmax", "l2")
