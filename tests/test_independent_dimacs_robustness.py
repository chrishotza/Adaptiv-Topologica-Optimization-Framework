from experiments.run_independent_dimacs_robustness import (
    exact_two_sided_sign_test,
    run_robustness,
)


def test_exact_sign_test_handles_ties():
    assert exact_two_sided_sign_test([0, 0, 1, -1]) == 1.0


def test_robustness_uses_majority_as_reference():
    payload = {
        "total_graphs": 2,
        "configs": {
            "demo": {
                "folds": {
                    "a": [
                        {
                            "nearest_relative_regret": 0.0,
                            "learned_relative_regret": 0.5,
                            "majority_relative_regret": 0.2,
                        }
                    ],
                    "b": [
                        {
                            "nearest_relative_regret": 0.1,
                            "learned_relative_regret": 0.0,
                            "majority_relative_regret": 0.2,
                        }
                    ],
                }
            }
        },
    }
    result = run_robustness(payload)
    nearest = result["results"]["demo"]["nearest"]
    centroid = result["results"]["demo"]["centroid"]

    assert nearest["mean_delta"] == -0.15
    assert centroid["mean_delta"] == 0.05
    assert nearest["better"] == 1
    assert nearest["worse"] == 1
