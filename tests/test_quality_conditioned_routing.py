from __future__ import annotations

from experiments.quality_conditioned_routing import QualityConditionedRouter


def _graph(graph_id: str, density: float, cut_a: float, cut_b: float) -> dict:
    return {
        "graph_id": graph_id,
        "corpus": "train",
        "edges": 100,
        "topology": {
            "density": density,
            "avg_degree": 2.0,
            "degree_std": 0.2,
            "hub_ratio": 1.1,
            "degree_gini": 0.1,
            "clustering": 0.2,
            "transitivity": 0.2,
            "core_number": 2.0,
            "diameter": 5.0,
            "avg_path_length": 2.0,
            "modularity": 0.2,
        },
        "oracle_strategy": "solver_a" if cut_a < cut_b else "solver_b",
        "strategy_metrics": {
            "solver_a": {"edge_cut": cut_a, "runtime_seconds": 0.1},
            "solver_b": {"edge_cut": cut_b, "runtime_seconds": 0.1},
        },
    }


def test_quality_router_uses_strategy_specific_outcomes() -> None:
    training = [
        _graph("g1", 0.10, 80.0, 120.0),
        _graph("g2", 0.20, 90.0, 110.0),
        _graph("g3", 0.80, 120.0, 70.0),
    ]
    router = QualityConditionedRouter(k_neighbors=3).fit(training)

    near_low = training[0]["topology"]
    scores_low = router.predict_scores(near_low)
    assert scores_low["solver_a"] < scores_low["solver_b"]
    assert router.rank(near_low)[0] == "solver_a"

    near_high = training[2]["topology"]
    scores_high = router.predict_scores(near_high)
    assert scores_high["solver_b"] < scores_high["solver_a"]
    assert router.rank(near_high)[0] == "solver_b"


def test_exact_training_match_is_deterministic() -> None:
    training = [
        _graph("g1", 0.10, 80.0, 120.0),
        _graph("g2", 0.20, 90.0, 110.0),
    ]
    router = QualityConditionedRouter(k_neighbors=3).fit(training)
    scores = router.predict_scores(training[0]["topology"])
    assert scores["solver_a"] == 0.8
    assert scores["solver_b"] == 1.2
