from __future__ import annotations

from experiments.confidence_gated_allocation import (
    _inner_margin_threshold,
)


def _graph(graph_id: str, density: float) -> dict:
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
        "oracle_strategy": "solver_a",
        "strategy_metrics": {
            "solver_a": {"edge_cut": 80.0, "runtime_seconds": 0.1},
            "solver_b": {"edge_cut": 100.0, "runtime_seconds": 0.2},
        },
    }


def test_inner_threshold_uses_training_topology_only() -> None:
    training = [
        _graph("g1", 0.10),
        _graph("g2", 0.20),
        _graph("g3", 0.30),
        _graph("g4", 0.40),
    ]
    threshold = _inner_margin_threshold(training, 0.50)
    assert threshold >= 0.0
