from atof.routing import (
    LearnedTopologyRouter,
    NearestTopologyRouter,
    evaluate_holdout_predictions,
    graph_oracle,
    routing_summary,
    topology_vector,
)


def test_topology_vector_is_finite():
    vector = topology_vector({"density": 0.2, "modularity": None})
    assert len(vector) == 11
    assert all(value == value for value in vector)


def test_router_fits_and_predicts():
    training = [
        {
            "graph": "hub",
            "topology": {"density": 0.1, "avg_degree": 10, "hub_ratio": 4},
            "oracle_strategy": "bloc_reloc_affinity",
        },
        {
            "graph": "regular",
            "topology": {"density": 0.5, "avg_degree": 4, "hub_ratio": 1},
            "oracle_strategy": "kernighan_lin",
        },
    ]
    router = LearnedTopologyRouter().fit(training)
    assert router.predict(
        {"density": 0.11, "avg_degree": 9.8, "hub_ratio": 3.9}
    ) == "bloc_reloc_affinity"


def test_graph_oracle_and_holdout_evaluation():
    rows = [
        {"graph": "g1", "strategy": "a", "edge_cut": 10},
        {"graph": "g1", "strategy": "b", "edge_cut": 8},
        {"graph": "g2", "strategy": "a", "edge_cut": 6},
        {"graph": "g2", "strategy": "b", "edge_cut": 7},
    ]
    assert graph_oracle(rows) == {"g1": "b", "g2": "a"}

    evaluations = evaluate_holdout_predictions(rows, {"g1": "b", "g2": "a"})
    summary = routing_summary(evaluations)
    assert summary["graphs"] == 2
    assert summary["oracle_agreement_rate"] == 1.0
    assert summary["mean_absolute_regret"] == 0.0


def test_nearest_router_fits_and_predicts():
    training = [
        {
            "graph": "hub",
            "topology": {"density": 0.1, "avg_degree": 10, "hub_ratio": 4},
            "oracle_strategy": "bloc_reloc_affinity",
        },
        {
            "graph": "regular",
            "topology": {"density": 0.5, "avg_degree": 4, "hub_ratio": 1},
            "oracle_strategy": "kernighan_lin",
        },
    ]
    router = NearestTopologyRouter().fit(training)
    assert router.predict(
        {"density": 0.11, "avg_degree": 9.8, "hub_ratio": 3.9}
    ) == "bloc_reloc_affinity"
