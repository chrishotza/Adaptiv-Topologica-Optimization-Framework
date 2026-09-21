import networkx as nx
import pytest

from experiments.run_metis_validation import rebalance_two_way_partition


def test_rebalance_two_way_partition_reaches_exact_balance():
    graph = nx.path_graph(6)
    membership = [0, 0, 0, 0, 1, 1]

    repaired, moves = rebalance_two_way_partition(graph, membership)

    assert sum(part == 0 for part in repaired) == 3
    assert sum(part == 1 for part in repaired) == 3
    assert moves == 1


def test_rebalance_two_way_partition_is_noop_when_balanced():
    graph = nx.cycle_graph(6)
    membership = [0, 0, 0, 1, 1, 1]

    repaired, moves = rebalance_two_way_partition(graph, membership)

    assert repaired == membership
    assert moves == 0


def test_rebalance_two_way_partition_rejects_invalid_membership():
    graph = nx.path_graph(4)

    with pytest.raises(ValueError):
        rebalance_two_way_partition(graph, [0, 1, 2, 0])

    with pytest.raises(ValueError):
        rebalance_two_way_partition(graph, [0, 1])
