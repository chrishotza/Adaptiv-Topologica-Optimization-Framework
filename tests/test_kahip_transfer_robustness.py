import json
from pathlib import Path


RESULT = Path("research/kahip-transfer-robustness.json")


def test_kahip_transfer_robustness_is_frozen():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["n_graphs"] == 17
    assert payload["added_strategy"] == "kahip_kaffpa_strong_balanced"
    assert payload["oracle_transition"]["graphs_changed_oracle"] == 13
    assert payload["oracle_transition"]["graphs_unchanged_oracle"] == 4
    assert payload["oracle_transition"]["kahip_graph_outcomes"] == {
        "strict_win": 7,
        "tie_min": 6,
        "loss": 4,
    }
    assert set(payload["paired_statistics"]) == {
        "all_iqr_l2",
        "global_paths_iqr_l2",
        "global_paths_minmax_l2",
    }


def test_nearest_neighbor_deltas_are_not_overstated():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    for config in payload["paired_statistics"].values():
        nearest = config["nearest"]
        assert -0.02 < nearest["mean_delta"] < 0.02
        assert nearest["exact_sign_flip_p_one_sided"] > 0.05
        lo, hi = nearest["bootstrap_95_ci"]
        assert lo < 0 < hi


def test_centroid_deltas_are_not_overstated():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    for config in payload["paired_statistics"].values():
        centroid = config["centroid"]
        assert centroid["mean_delta"] < 0
        assert centroid["exact_sign_flip_p_one_sided"] > 0.05
        lo, hi = centroid["bootstrap_95_ci"]
        assert lo < 0 < hi


def test_majority_delta_is_marked_as_rebaseline():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    notes = " ".join(payload["notes"])
    assert "re-baselining" in notes
    assert "not an isolated effect" in notes
