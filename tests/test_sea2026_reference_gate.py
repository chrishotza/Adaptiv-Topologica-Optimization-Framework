from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from experiments.run_sea2026_reference_gate import (
    balance_bound_ok,
    build_command,
    parse_partition,
    partition_file_for,
)

def test_command_uses_builtin_default_preset_type() -> None:
    command = build_command(
        Path("/tmp/MtKaHyPar"),
        Path("/tmp/sample.graph"),
        Path("/tmp/output"),
        k=4,
        seed=1,
        threads=4,
        epsilon=0.03,
        learned=True,
    )
    assert "--preset-type=default" in command
    assert "--preset=default" not in command


def test_partition_parser_requires_exact_node_count(tmp_path: Path) -> None:
    path = tmp_path / "graph.part4.epsilon0.03.seed1.KaHyPar"
    path.write_text("0\n1\n2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="partition length"):
        parse_partition(path, 4)


def test_partition_parser_accepts_one_block_id_per_line(tmp_path: Path) -> None:
    path = tmp_path / "graph.part4.epsilon0.03.seed1.KaHyPar"
    path.write_text("0\n1\n1\n0\n", encoding="utf-8")
    assert parse_partition(path, 4, 2) == [0, 1, 1, 0]


def test_partition_parser_rejects_out_of_range_block_id(tmp_path: Path) -> None:
    path = tmp_path / "graph.part4.epsilon0.03.seed1.KaHyPar"
    path.write_text("0\n1\n4\n0\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"outside \[0, 4\)"):
        parse_partition(path, 4, 4)


def test_partition_filename_matches_sea_snapshot_convention(tmp_path: Path) -> None:
    graph = tmp_path / "sample.graph"
    observed = partition_file_for(tmp_path, graph, 8, 0.03, 4)
    assert observed.name == "sample.graph.part8.epsilon0.03.seed4.KaHyPar"


def test_balance_bound_rejects_empty_block() -> None:
    graph = nx.path_graph(1000)
    counts = [16] * 62 + [8, 0]
    assert sum(counts) == graph.number_of_nodes()
    assert not balance_bound_ok(graph, counts, 64, 0.03)


def test_balance_bound_uses_sea_epsilon() -> None:
    graph = nx.path_graph(10)
    assert balance_bound_ok(graph, [3, 3, 2, 2], 4, 0.03)
    assert not balance_bound_ok(graph, [4, 3, 2, 1], 4, 0.03)
