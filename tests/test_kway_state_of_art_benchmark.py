from __future__ import annotations

import pytest

from experiments.run_kway_state_of_art_benchmark import (
    K_VALUES,
    STRATEGIES,
    _aggregate,
    _summarize_graph,
)


def test_worker_decoder_uses_last_nonempty_stdout_line() -> None:
    from experiments.run_kway_state_of_art_benchmark import _decode_worker_rows

    assert _decode_worker_rows('native warning\n[{"status": "ok"}]\n') == [
        {"status": "ok"}
    ]
    with pytest.raises(ValueError, match="must be a list"):
        _decode_worker_rows('{"status": "ok"}\n')


def test_kway_surface_matches_locked_protocol() -> None:
    assert K_VALUES == (4, 8, 32, 64)
    assert len(STRATEGIES) == 10
    assert "metis" in STRATEGIES
    assert "kahip" in STRATEGIES
    assert "kaminpar_default" in STRATEGIES
    assert "kaminpar_strong" in STRATEGIES
    assert "mtkahypar_default" in STRATEGIES
    assert "mtkahypar_quality" in STRATEGIES


def test_unmatched_graphs_do_not_enter_aggregate() -> None:
    rows = [
        {
            "strategy": "a",
            "status": "ok",
            "edge_cut": 10,
            "balance_error": 0.0,
            "runtime_seconds": 2.0,
        },
        {
            "strategy": "b",
            "status": "ok",
            "edge_cut": 10,
            "balance_error": 0.0,
            "runtime_seconds": 1.0,
        },
        {
            "strategy": "c",
            "status": "error",
            "error": "backend unavailable",
        },
    ]
    summary = _summarize_graph(rows, ("a", "b", "c"))
    assert summary["matched"] is False
    assert _aggregate({"g": summary}, ("a", "b", "c"))["matched_graphs"] == 0


def test_duplicate_seed_rows_are_not_matched() -> None:
    rows = [
        *[
            {"strategy": "a", "status": "ok", "seed": seed, "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 2.0}
            for seed in (42, 101, 42)
        ],
        *[
            {"strategy": "b", "status": "ok", "seed": seed, "edge_cut": 12, "balance_error": 0.0, "runtime_seconds": 1.0}
            for seed in (42, 101, 2024)
        ],
    ]
    summary = _summarize_graph(
        rows,
        ("a", "b"),
        expected_runs=3,
        expected_seeds=(42, 101, 2024),
    )
    assert summary["matched"] is False
    assert summary["incomplete_strategies"] == ["a"]


def test_incomplete_seed_set_is_not_matched() -> None:
    rows = [
        *[
            {"strategy": "a", "status": "ok", "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 2.0}
            for _ in range(3)
        ],
        *[
            {"strategy": "b", "status": "ok", "edge_cut": 12, "balance_error": 0.0, "runtime_seconds": 1.0}
            for _ in range(2)
        ],
    ]
    summary = _summarize_graph(rows, ("a", "b"), expected_runs=3)
    assert summary["matched"] is False
    assert summary["incomplete_strategies"] == ["b"]
    assert _aggregate({"g": summary}, ("a", "b"))["matched_graphs"] == 0


def test_matched_graph_is_aggregated() -> None:
    rows = [
        {"strategy": "a", "status": "ok", "edge_cut": 10, "balance_error": 0.0, "runtime_seconds": 2.0},
        {"strategy": "b", "status": "ok", "edge_cut": 12, "balance_error": 0.0, "runtime_seconds": 1.0},
    ]
    summary = _summarize_graph(rows, ("a", "b"))
    assert summary["matched"] is True
    assert summary["best_quality"] == "a"
    aggregate = _aggregate({"g": summary}, ("a", "b"))
    assert aggregate["matched_graphs"] == 1
    assert aggregate["strategies"]["a"]["mean_relative_quality_gap"] == pytest.approx(0.0)
    assert aggregate["strategies"]["b"]["mean_relative_quality_gap"] == pytest.approx(0.2)

def test_selected_k_values_are_allowed() -> None:
    from experiments.run_kway_state_of_art_benchmark import K_VALUES, run_kway_state_of_art_benchmark

    assert K_VALUES == (4, 8, 32, 64)
    import inspect
    signature = inspect.signature(run_kway_state_of_art_benchmark)
    assert signature.parameters["k_values"].default == K_VALUES

def test_exact_floor_ceil_balance_gate():
    import networkx as nx
    from experiments.run_kway_state_of_art_benchmark import (
        _exact_partition_balance_error,
        _expected_balance_error,
        _validate_exact_balance_error,
    )
    from atof.partition import rebalance_kway

    graph = nx.path_graph(10)

    assert _expected_balance_error(graph, 3) == pytest.approx(0.2)
    assert _validate_exact_balance_error(graph, 3, 0.2)
    assert not _validate_exact_balance_error(graph, 3, 0.4)

    graph_33 = nx.path_graph(33)
    valid = {
        node: block
        for block in range(8)
        for node in range(
            sum(5 if i < 1 else 4 for i in range(block)),
            sum(5 if i < 1 else 4 for i in range(block + 1)),
        )
    }
    assert _exact_partition_balance_error(graph_33, valid, 8) == pytest.approx(7 / 33)
    invalid = dict(valid)
    invalid[32] = 0
    with pytest.raises(ValueError, match="floor/ceil"):
        _exact_partition_balance_error(graph_33, invalid, 8)

    repaired = rebalance_kway(
        graph_33,
        [0] * 33,
        8,
    )
    assert sorted(repaired.count(block) for block in range(8)) == [4, 4, 4, 4, 4, 4, 4, 5]

    graph_15 = nx.path_graph(15)
    observed = [0, 1, 2, 3, 4, 5, 6, 7, 1, 2, 2, 3, 5, 6, 7]
    repaired_15 = rebalance_kway(graph_15, observed, 8)
    assert sorted(repaired_15.count(block) for block in range(8)) == [1, 2, 2, 2, 2, 2, 2, 2]

    graph_skew = nx.path_graph(33)
    already_under_upper = [0] + [1] * 5 + [2] * 5 + [3] * 5 + [4] * 5 + [5] * 5 + [6] * 4 + [7] * 4
    repaired_skew = rebalance_kway(graph_skew, already_under_upper, 8)
    assert sorted(repaired_skew.count(block) for block in range(8)) == [4, 4, 4, 4, 4, 4, 4, 5]
