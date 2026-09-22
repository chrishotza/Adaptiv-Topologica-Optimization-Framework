from __future__ import annotations

import networkx as nx

from experiments.mtkahypar_backend import _write_metis_graph


def test_write_metis_graph_uses_one_based_adjacency(tmp_path) -> None:
    graph = nx.path_graph(3)
    path = tmp_path / "path.metis"
    _write_metis_graph(graph, path)
    assert path.read_text(encoding="utf-8").splitlines() == [
        "3 2",
        "2",
        "1 3",
        "2",
    ]