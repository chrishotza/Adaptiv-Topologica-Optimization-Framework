import networkx as nx
import pytest
from atof.partition import balance_error, edge_cut, initialize_balanced_partition
from atof.strategies import BLOCReloc

def test_balanced_initialization():
    g=nx.path_graph(10); p=initialize_balanced_partition(g,2)
    assert list(p.values()).count(0)==5 and list(p.values()).count(1)==5
    assert balance_error(g,p,2)==0

def test_edge_cut():
    g=nx.path_graph(4); p={0:0,1:0,2:1,3:1}
    assert edge_cut(g,p)==1

def test_bloc_returns_balanced_partition():
    result=BLOCReloc(nx.cycle_graph(20),k=4,seed=42).refine(iterations=5)
    assert len(result.partition)==20 and result.balance_error<=0.05 and result.edge_cut>=0

def test_invalid_k():
    with pytest.raises(ValueError): BLOCReloc(nx.path_graph(3),k=4)
