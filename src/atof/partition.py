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

def exact_partition_balance_error(
    graph: nx.Graph,
    partition: Mapping[Node, int],
    k: int,
) -> float:
    """Validate floor/ceil block sizes and return the research balance metric."""
    _validate_partition(graph, partition, k)
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    counts = [sum(1 for block in partition.values() if block == target) for target in range(k)]
    expected = sorted(exact_balanced_block_weights(n, k))
    observed = sorted(counts)
    if observed != expected:
        raise ValueError(
            "partition is outside the exact floor/ceil balance contract"
            f"; n={n}, k={k}, counts={counts}, expected={expected}"
        )
    target = n / k
    lower = n // k
    upper = (n + k - 1) // k
    return max(abs(lower - target), abs(upper - target)) / target


def rebalance_kway(
    graph: nx.Graph,
    membership: list[int],
    k: int,
) -> list[int]:
    """Repair a k-way membership to exact floor/ceil sizes with local moves."""
    if len(membership) != graph.number_of_nodes():
        raise ValueError("membership length must match graph node count")
    if k < 2:
        raise ValueError("k must be at least 2")
    if any(block < 0 or block >= k for block in membership):
        raise ValueError("membership contains an invalid block label")

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    result = list(membership)
    counts = [result.count(block) for block in range(k)]
    lower = graph.number_of_nodes() // k
    upper = (graph.number_of_nodes() + k - 1) // k

    expected = sorted(exact_balanced_block_weights(graph.number_of_nodes(), k))

    while True:
        if sorted(counts) == expected:
            return result

        oversized = [block for block, count in enumerate(counts) if count > upper]
        if oversized:
            source = min(oversized)
            targets = tuple(
                block for block, count in enumerate(counts) if count < upper
            )
        else:
            undersized = [block for block, count in enumerate(counts) if count < lower]
            if not undersized:
                raise RuntimeError(
                    "could not repair partition balance"
                    f"; n={graph.number_of_nodes()}, k={k}, counts={counts}, "
                    f"lower={lower}, upper={upper}, membership_len={len(result)}"
                )
            source = min(
                block for block, count in enumerate(counts) if count > lower
            )
            targets = tuple(undersized)
        candidates: list[tuple[int, str, int, int]] = []
        for node in nodes:
            i = index[node]
            if result[i] != source:
                continue
            source_neighbors = sum(
                1
                for neighbor in graph.neighbors(node)
                if result[index[neighbor]] == source
            )
            for target in targets:
                target_neighbors = sum(
                    1
                    for neighbor in graph.neighbors(node)
                    if result[index[neighbor]] == target
                )
                delta = source_neighbors - target_neighbors
                candidates.append((delta, repr(node), i, target))

        if not candidates:
            raise RuntimeError(
                "could not repair partition balance"
                f"; n={graph.number_of_nodes()}, k={k}, counts={counts}, "
                f"lower={lower}, upper={upper}, membership_len={len(result)}"
            )

        _, _, chosen, target = min(candidates)
        result[chosen] = target
        counts[source] -= 1
        counts[target] += 1



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
