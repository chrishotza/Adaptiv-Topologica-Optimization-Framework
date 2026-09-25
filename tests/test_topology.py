import math

import networkx as nx
import pytest

import atof.topology as topology
from atof.topology import TopologyProfiler, resolve_profile_features


def test_topology_profile_basic_fields():
    profile = TopologyProfiler().profile(nx.path_graph(8))
    assert (
        profile.node_count == 8
        and profile.edge_count == 7
        and profile.max_degree == 2
        and profile.avg_degree > 0
    )


def test_regular_graph_assortativity_does_not_emit_runtime_warning():
    import warnings

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        profile = TopologyProfiler().profile(nx.cycle_graph(8))

    assert not [
        warning for warning in captured if warning.category is RuntimeWarning
    ]
    assert isinstance(profile.assortativity, float)


def test_profile_feature_subset_skips_unrequested_expensive_descriptors(
    monkeypatch: pytest.MonkeyPatch,
):
    graph = nx.gnp_random_graph(24, 0.15, seed=7)
    expensive = (
        "average_clustering",
        "transitivity",
        "degree_assortativity_coefficient",
        "core_number",
        "diameter",
        "average_shortest_path_length",
    )

    def fail(*args, **kwargs):
        raise AssertionError("unrequested topology computation was executed")

    for name in expensive:
        monkeypatch.setattr(getattr(topology.nx, name), "__call__", fail, raising=False)

    profiler = TopologyProfiler(
        features=(
            "density",
            "avg_degree",
            "degree_std",
            "hub_ratio",
            "degree_gini",
        )
    )
    profile = profiler.profile(graph)

    assert math.isfinite(profile.density)
    assert math.isfinite(profile.avg_degree)
    assert math.isfinite(profile.degree_std)
    assert math.isfinite(profile.hub_ratio)
    assert math.isfinite(profile.degree_gini)
    assert math.isnan(profile.clustering)
    assert math.isnan(profile.transitivity)
    assert math.isnan(profile.assortativity)
    assert math.isnan(profile.core_number)
    assert math.isnan(profile.diameter)
    assert math.isnan(profile.avg_path_length)
    assert math.isnan(profile.modularity)


def test_profile_feature_subset_can_be_overridden_per_call():
    graph = nx.path_graph(8)
    profiler = TopologyProfiler(features=("density",))
    profile = profiler.profile(
        graph,
        features=("density", "diameter"),
    )

    assert math.isfinite(profile.density)
    assert profile.diameter == 7.0
    assert math.isnan(profile.avg_degree)


def test_profile_feature_validation():
    assert resolve_profile_features(("density", "diameter")) == (
        "density",
        "diameter",
    )
    with pytest.raises(ValueError, match="unknown topology profile features"):
        resolve_profile_features(("not_a_feature",))
    with pytest.raises(ValueError, match="duplicates"):
        resolve_profile_features(("density", "density"))
