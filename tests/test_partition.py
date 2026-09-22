import networkx as nx
import pytest
from atof.partition import (
    balance_error,
    edge_cut,
    exact_balanced_block_weights,
    initialize_balanced_partition,
)
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


def test_bloc_preserves_floor_ceil_balance():
    result = BLOCReloc(nx.cycle_graph(21), k=4, seed=42).refine(iterations=5)
    counts = [list(result.partition.values()).count(block) for block in range(4)]
    assert sorted(counts) == [5, 5, 5, 6]


def test_bloc_move_delta_matches_full_objective():
    graph = nx.gnp_random_graph(30, 0.15, seed=7)
    for variant in ("baseline", "affinity"):
        bloc = BLOCReloc(graph, k=2, seed=42, variant=variant)
        partition = initialize_balanced_partition(graph, 2)
        node = next(iter(graph.nodes()))
        source = partition[node]
        target = 1 - source
        before = bloc._objective(partition)
        partition[node] = target
        after = bloc._objective(partition)
        partition[node] = source
        assert abs((after - before) - bloc._move_delta(node, source, target, partition)) < 1e-12


def test_bloc_swap_delta_matches_full_objective():
    graph = nx.gnp_random_graph(40, 0.12, seed=11)
    for variant in ("baseline", "affinity"):
        bloc = BLOCReloc(graph, k=3, seed=42, variant=variant)
        partition = initialize_balanced_partition(graph, 3)
        nodes = list(graph.nodes())
        for u, v in zip(nodes[::3], nodes[1::3]):
            if partition[u] == partition[v]:
                continue
            before = bloc._objective(partition)
            delta = bloc._swap_delta(u, v, partition)
            bu, bv = partition[u], partition[v]
            partition[u], partition[v] = bv, bu
            after = bloc._objective(partition)
            partition[u], partition[v] = bu, bv
            assert abs((after - before) - delta) < 1e-12


def test_exact_balanced_block_weights():
    assert exact_balanced_block_weights(10, 3) == [4, 3, 3]
    assert exact_balanced_block_weights(21, 4) == [6, 5, 5, 5]
    assert exact_balanced_block_weights(20, 4) == [5, 5, 5, 5]


@pytest.mark.parametrize("n,k", [(0, 1), (2, 3)])
def test_exact_balanced_block_weights_rejects_invalid_inputs(n, k):
    with pytest.raises(ValueError):
        exact_balanced_block_weights(n, k)
