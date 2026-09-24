from pathlib import Path
import json
from experiments.k8_degree_hub_online_selector import _predict_alternate, FEATURES, K, SEEDS

def test_protocol_is_frozen():
    assert K == 8
    assert SEEDS == (7, 42, 101, 2024, 8191)
    assert FEATURES == ("density","avg_degree","degree_std","hub_ratio","degree_gini")

def test_negative_prediction_selects_alternate():
    candidate, prediction = _predict_alternate(
        ("a","b","c"),
        pair_median={("a","b"):0.1, ("a","c"):-0.2},
        candidate_median={}, rank_median={}
    )
    assert candidate == "c"
    assert prediction < 0
