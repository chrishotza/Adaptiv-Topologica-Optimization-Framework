from atof.routing import (
    FEATURE_GROUPS,
    LearnedTopologyRouter,
    NearestTopologyRouter,
)


def test_scaling_and_metric_modes_validate():
    training = [
        {
            "graph": "a",
            "topology": {
                "core_number": 2,
                "diameter": 4,
                "avg_path_length": 2.0,
            },
            "oracle_strategy": "x",
        },
        {
            "graph": "b",
            "topology": {
                "core_number": 5,
                "diameter": 8,
                "avg_path_length": 5.0,
            },
            "oracle_strategy": "y",
        },
    ]

    router = NearestTopologyRouter(
        features=FEATURE_GROUPS["global_paths"],
        scale_mode="iqr",
        metric="l1",
    ).fit(training)

    assert router.features == FEATURE_GROUPS["global_paths"]
    assert router.scale_mode == "iqr"
    assert router.metric == "l1"
    assert router.predict(training[0]["topology"]) == "x"

    centroid = LearnedTopologyRouter(
        features=FEATURE_GROUPS["global_paths"],
        scale_mode="std",
        metric="l2",
    ).fit(training)
    assert centroid.predict(training[1]["topology"]) == "y"
