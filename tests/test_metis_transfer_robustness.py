import json
from pathlib import Path


RESULT = Path("research/metis-transfer-statistical-robustness.json")


def test_metis_robustness_result_is_frozen_and_complete():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["n_graphs"] == 17
    assert payload["added_strategy"] == "metis_multilevel_balanced"
    assert set(payload["paired_statistics"]) == {
        "all_iqr_l2",
        "global_paths_iqr_l2",
        "global_paths_minmax_l2",
    }


def test_nearest_neighbor_improvement_is_consistent():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    for config in payload["paired_statistics"].values():
        nearest = config["nearest"]
        assert nearest["mean_delta"] < 0
        assert nearest["exact_sign_flip_p_one_sided"] < 0.01
        assert nearest["worsened"] < nearest["improved"]


def test_centroid_result_is_not_overstated():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    centroid = payload["paired_statistics"]
    for config in centroid.values():
        p = config["centroid"]["exact_sign_flip_p_one_sided"]
        assert p > 0.05
