from __future__ import annotations

from pathlib import Path

from atof.dimacs import _parse_metis_graph


def _bz2_graph(text: str) -> bytes:
    import bz2
    return bz2.compress(text.encode("utf-8"))


def test_parse_plain_metis_graph():
    payload = _bz2_graph(
        "% comment\n"
        "3 2\n"
        "2\n"
        "1 3\n"
        "2\n"
    )
    graph = _parse_metis_graph(payload)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2


def test_parse_metis_edge_weights_ignores_weights():
    payload = _bz2_graph(
        "3 2 1\n"
        "2 7\n"
        "1 9 3 4\n"
        "2 4\n"
    )
    graph = _parse_metis_graph(payload)
    assert graph.number_of_nodes() == 3
    assert set(map(frozenset, graph.edges())) == {
        frozenset((0, 1)),
        frozenset((1, 2)),
    }


def test_parse_metis_preserves_isolated_vertex_lines():
    payload = _bz2_graph(
        "3 1\n"
        "2\n"
        "\n"
        "1\n"
    )
    graph = _parse_metis_graph(payload)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 1
    assert list(graph.neighbors(1)) == []


def test_parser_file_is_in_package():
    assert Path("src/atof/dimacs.py").exists()
