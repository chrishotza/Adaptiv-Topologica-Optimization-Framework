from experiments.run_generalization_study import combine_routing_payloads


def _fold(graph, oracle, learned, global_strategy, heuristic, regret):
    return {
        "held_out_graph": graph,
        "oracle_strategy": oracle,
        "learned_strategy": learned,
        "global_strategy": global_strategy,
        "heuristic_strategy": heuristic,
        "learned_absolute_regret": regret,
        "global_absolute_regret": regret * 2,
        "heuristic_absolute_regret": regret / 2,
        "learned_relative_regret": regret,
        "global_relative_regret": regret * 2,
        "heuristic_relative_regret": regret / 2,
    }


def test_combine_routing_payloads_preserves_corpus_boundaries():
    payload = combine_routing_payloads(
        {
            "development": {
                "protocol": "leave-one-graph-out",
                "folds": [
                    _fold("dev-a", "a", "a", "b", "a", 0.0),
                    _fold("dev-b", "b", "a", "b", "b", 0.1),
                ],
            },
            "external": {
                "routing": {
                    "protocol": "leave-one-graph-out",
                    "folds": [
                        _fold("ext-a", "a", "a", "a", "b", 0.2),
                    ],
                }
            },
        }
    )

    assert payload["unit_of_analysis"] == "held-out graph"
    assert payload["summary"]["corpus_count"] == 2
    assert payload["summary"]["graph_count"] == 3
    assert payload["corpora"]["development"]["graphs"] == 2
    assert payload["corpora"]["external"]["graphs"] == 1
