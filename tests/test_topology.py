import math

import networkx as nx
import pytest

from atof.topology import (
    PROFILE_EXPENSIVE_NODE_LIMIT,
    PROFILE_MODULARITY_NODE_LIMIT,
    TopologyProfiler,
)


def test_topology_profile_basic_fields():
    profile = TopologyProfiler().profile(nx.path_graph(8))
    assert (
        profile.node_count == 8
        and profile.edge_count == 7
        and profile.max_degree == 2
        and profile.avg_degree > 0
    )


def test_bounded_matches_full_on_small_graph():
    graph = nx.cycle_graph(12)
    full = TopologyProfiler().profile(graph, mode="full")
    bounded = TopologyProfiler().profile(graph, mode="bounded")
    assert bounded == full


def test_bounded_skips_expensive_metrics_for_large_graph(monkeypatch):
    graph = nx.path_graph(PROFILE_EXPENSIVE_NODE_LIMIT + 1)
    profiler = TopologyProfiler()

    def fail(*args, **kwargs):
        raise AssertionError("expensive operation was called")

    monkeypatch.setattr(nx, "diameter", fail)
    monkeypatch.setattr(nx, "average_shortest_path_length", fail)

    bounded = profiler.profile(graph, mode="bounded")
    assert math.isnan(bounded.diameter)
    assert math.isnan(bounded.avg_path_length)


def test_bounded_skips_modularity_for_large_graph(monkeypatch):
    graph = nx.path_graph(PROFILE_MODULARITY_NODE_LIMIT + 1)

    import networkx.algorithms.community as community

    def fail(*args, **kwargs):
        raise AssertionError("greedy modularity was called")

    monkeypatch.setattr(community, "greedy_modularity_communities", fail)

    bounded = TopologyProfiler().profile(graph, mode="bounded")
    assert bounded.communities == 0
    assert math.isnan(bounded.modularity)


def test_invalid_profile_mode_and_limits():
    graph = nx.path_graph(4)
    with pytest.raises(ValueError, match="unknown topology profile mode"):
        TopologyProfiler().profile(graph, mode="fast")
    with pytest.raises(ValueError, match="expensive_node_limit"):
        TopologyProfiler().profile(graph, expensive_node_limit=0)
    with pytest.raises(ValueError, match="modularity_node_limit"):
        TopologyProfiler().profile(graph, modularity_node_limit=0)
