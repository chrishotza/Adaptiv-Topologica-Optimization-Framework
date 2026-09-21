from atof.routing import FEATURE_ABLATIONS, LearnedTopologyRouter, NearestTopologyRouter


def test_feature_ablation_sets_are_valid_and_distinct():
    assert set(FEATURE_ABLATIONS) == {
        "all",
        "without_degree_hub",
        "without_mesoscopic",
        "without_global_paths",
        "without_degree_hub_mesoscopic",
        "without_degree_hub_global_paths",
        "without_mesoscopic_global_paths",
    }
    assert FEATURE_ABLATIONS["all"]
    assert all(FEATURE_ABLATIONS[name] for name in FEATURE_ABLATIONS)

    assert LearnedTopologyRouter(
        features=FEATURE_ABLATIONS["without_degree_hub"]
    ).features == FEATURE_ABLATIONS["without_degree_hub"]
    assert NearestTopologyRouter(
        features=FEATURE_ABLATIONS["without_mesoscopic"]
    ).features == FEATURE_ABLATIONS["without_mesoscopic"]


def test_feature_set_aggregation_accepts_iterables():
    from experiments.run_feature_ablation import _mean

    assert _mean(value for value in (1.0, 2.0, 3.0)) == 2.0
