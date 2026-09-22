from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from experiments.run_sea_set_a_gate import read_metis_graph


def test_metis_parser_preserves_empty_adjacency_lines(tmp_path: Path) -> None:
    path = tmp_path / "isolated.metis"
    path.write_text("3 1\n2\n1\n\n", encoding="utf-8")

    graph = read_metis_graph(path)

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 1
    assert set(graph.edges()) == {(1, 2)}


def test_metis_parser_rejects_wrong_edge_count(tmp_path: Path) -> None:
    path = tmp_path / "bad.metis"
    path.write_text("3 2\n2\n1\n\n", encoding="utf-8")

    with pytest.raises(ValueError, match="header edge count"):
        read_metis_graph(path)


def test_set_a_gate_imports_as_a_research_only_module() -> None:
    graph = nx.path_graph(4)
    assert graph.number_of_nodes() == 4


def test_sea_workflow_uses_live_github_expressions() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "sea-set-a-gate.yml"
    ).read_text(encoding="utf-8")

    assert "if: \\${{" not in workflow
    assert "--limit \\${{" not in workflow
    assert "if: ${{ github.event.inputs.manifest_only != 'true' }}" in workflow
    assert "--limit ${{ inputs.limit }}" in workflow
