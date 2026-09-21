import networkx as nx
from atof.topology import TopologyProfiler

def test_topology_profile_basic_fields():
    profile=TopologyProfiler().profile(nx.path_graph(8))
    assert profile.node_count==8 and profile.edge_count==7 and profile.max_degree==2 and profile.avg_degree>0
