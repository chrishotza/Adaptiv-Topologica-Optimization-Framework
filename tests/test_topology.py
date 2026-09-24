import networkx as nx
from atof.topology import TopologyProfiler

def test_topology_profile_basic_fields():
    profile=TopologyProfiler().profile(nx.path_graph(8))
    assert profile.node_count==8 and profile.edge_count==7 and profile.max_degree==2 and profile.avg_degree>0


def test_regular_graph_assortativity_does_not_emit_runtime_warning():
    import warnings
    import networkx as nx

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        profile = TopologyProfiler().profile(nx.cycle_graph(8))

    assert not [warning for warning in captured if warning.category is RuntimeWarning]
    assert isinstance(profile.assortativity, float)
