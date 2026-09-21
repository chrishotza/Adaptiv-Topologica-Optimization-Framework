import pytest

pytest.importorskip("kahip")
pytest.importorskip("pymetis")

from experiments.run_router_confirmatory import LOCKED_CONFIGS
from experiments.run_router_kahip_confirmatory import KAHIP_STRATEGY


def test_expanded_protocol_is_nine_strategy():
    assert len(LOCKED_CONFIGS) == 3
    assert KAHIP_STRATEGY == "kahip_kaffpa_strong_balanced"


def test_expanded_corpus_definition_is_four_tiers():
    from experiments.run_expanded_20graph_kahip_transfer import EXPECTED_TOTAL_GRAPHS

    assert EXPECTED_TOTAL_GRAPHS == 20
