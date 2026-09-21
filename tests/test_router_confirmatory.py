from experiments.run_router_confirmatory import LOCKED_CONFIGS


def test_confirmatory_configuration_lock():
    assert set(LOCKED_CONFIGS) == {
        "all_iqr_l2",
        "global_paths_iqr_l2",
        "global_paths_minmax_l2",
    }
    assert LOCKED_CONFIGS["all_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_minmax_l2"][1:] == ("minmax", "l2")
