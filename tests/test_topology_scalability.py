import networkx as nx

from atof.topology import (
    TopologyProfiler,
    _average_shortest_path_length_exact,
)


def test_exact_average_shortest_path_matches_networkx():
    graph = nx.grid_2d_graph(8, 8)
    expected = nx.average_shortest_path_length(graph)
    actual = _average_shortest_path_length_exact(graph)
    assert actual == expected


def test_large_path_helper_matches_networkx_exactly():
    graph = nx.path_graph(2001)
    expected = nx.average_shortest_path_length(graph)
    actual = _average_shortest_path_length_exact(graph)
    assert actual == expected


def test_diameter_uses_exact_value():
    graph = nx.path_graph(2001)
    profile = TopologyProfiler().profile(graph)
    assert profile.diameter == 2000.0
