import pytest

pytest.importorskip("kahip")
pytest.importorskip("pymetis")

from experiments.run_kahip_validation import STRATEGY as KAHIP_STRATEGY
from experiments.run_metis_validation import STRATEGY as METIS_STRATEGY
from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_kahip_confirmatory import (
    EXPECTED_BASE_STRATEGY_COUNT,
    EXPECTED_EXPANDED_STRATEGY_COUNT,
)


def test_kahip_confirmatory_candidate_counts():
    assert EXPECTED_BASE_STRATEGY_COUNT == 8
    assert EXPECTED_EXPANDED_STRATEGY_COUNT == 9
    assert METIS_STRATEGY == "metis_multilevel_balanced"
    assert KAHIP_STRATEGY == "kahip_kaffpa_strong_balanced"


def test_kahip_confirmatory_keeps_locked_configurations():
    assert set(LOCKED_CONFIGS) == {
        "all_iqr_l2",
        "global_paths_iqr_l2",
        "global_paths_minmax_l2",
    }
    assert LOCKED_CONFIGS["all_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_iqr_l2"][1:] == ("iqr", "l2")
    assert LOCKED_CONFIGS["global_paths_minmax_l2"][1:] == ("minmax", "l2")
