from __future__ import annotations
from collections import Counter
from typing import Callable, Hashable, Mapping
import networkx as nx

Node = Hashable
Partition = dict[Node, int]
EdgeCost = Callable[[Node, Node], float]

def exact_balanced_block_weights(n: int, k: int) -> list[int]:
    """Return k floor/ceil block capacities summing exactly to n."""
    if k < 1:
        raise ValueError("k must be >= 1")
    if n < k:
        raise ValueError("n must be >= k")
    lower = n // k
    upper = (n + k - 1) // k
    num_upper = n - (lower * k)
    return [upper] * num_upper + [lower] * (k - num_upper)


def initialize_balanced_partition(graph: nx.Graph, k: int) -> Partition:
    """Create a deterministic near-balanced k-way partition."""
    if k < 1:
        raise ValueError("k must be >= 1")
    return {node: i % k for i, node in enumerate(graph.nodes())}

def _validate_partition(graph: nx.Graph, partition: Mapping[Node, int], k: int) -> None:
    missing = set(graph.nodes()) - set(partition)
    if missing:
        raise ValueError(f"partition is missing {len(missing)} graph nodes")
    if any(label < 0 or label >= k for label in partition.values()):
        raise ValueError("partition labels must be in [0, k)")

def edge_cut(graph: nx.Graph, partition: Mapping[Node, int]) -> int:
    """Count edges crossing between blocks."""
    return sum(partition[u] != partition[v] for u, v in graph.edges())

def weighted_cut(graph: nx.Graph, partition: Mapping[Node, int], edge_cost: EdgeCost) -> float:
    """Sum custom edge costs for crossing edges."""
    return sum(edge_cost(u, v) for u, v in graph.edges() if partition[u] != partition[v])

def balance_error(graph: nx.Graph, partition: Mapping[Node, int], k: int) -> float:
    """Normalized node-count imbalance; 0 means perfectly balanced."""
    _validate_partition(graph, partition, k)
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    counts = Counter(partition.values())
    target = n / k
    return sum(abs(counts.get(block, 0) - target) for block in range(k)) / n
