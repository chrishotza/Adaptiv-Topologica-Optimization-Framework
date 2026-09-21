from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Hashable, Mapping

import networkx as nx

from .partition import (
    Partition,
    balance_error,
    edge_cut,
    initialize_balanced_partition,
    weighted_cut,
)


@dataclass(frozen=True)
class PartitionResult:
    partition: Partition
    edge_cut: int
    weighted_cost: float
    balance_error: float
    iterations: int
    accepted_moves: int
    rejected_moves: int
    trace: tuple[dict[str, float | int], ...] = field(default_factory=tuple)


class BLOCReloc:
    """Balanced local graph partition refinement.

    The canonical public implementation is deterministic for a given seed and
    exposes baseline and degree-affinity objectives.
    """

    def __init__(
        self,
        graph: nx.Graph,
        k: int = 4,
        seed: int = 42,
        variant: str = "baseline",
    ) -> None:
        if k < 1:
            raise ValueError("k must be >= 1")
        if graph.number_of_nodes() < k:
            raise ValueError("k cannot exceed the number of graph nodes")
        if variant not in {"baseline", "affinity"}:
            raise ValueError("variant must be 'baseline' or 'affinity'")

        self.graph = graph
        self.k = k
        self.variant = variant
        self.rng = random.Random(seed)
        self.degree = dict(graph.degree())

    def edge_cost(self, u: Hashable, v: Hashable) -> float:
        if self.variant == "baseline":
            return 1.0
        return 1.0 / math.sqrt(self.degree[u] * self.degree[v] + 1.0)

    def _objective(self, partition: Mapping[Hashable, int]) -> float:
        return weighted_cut(self.graph, partition, self.edge_cost)

    def refine(
        self,
        iterations: int = 25,
        tolerance: float = 0.05,
        hybrid_period: int | None = None,
        hybrid_samples: int = 1000,
    ) -> PartitionResult:
        if iterations < 1:
            raise ValueError("iterations must be >= 1")
        if tolerance < 0:
            raise ValueError("tolerance must be >= 0")
        if hybrid_samples < 0:
            raise ValueError("hybrid_samples must be >= 0")

        partition = initialize_balanced_partition(self.graph, self.k)
        counts = {block: 0 for block in range(self.k)}
        for block in partition.values():
            counts[block] += 1

        best = self._objective(partition)
        accepted = 0
        rejected = 0
        trace: list[dict[str, float | int]] = []

        node_count = self.graph.number_of_nodes()
        ideal = node_count / self.k
        lower_size = node_count // self.k
        upper_size = math.ceil(node_count / self.k)
        # Keep partitions exactly balanced when n is divisible by k and
        # otherwise allow only floor(n/k) or ceil(n/k) nodes per block.
        del ideal  # The canonical movement rule uses exact floor/ceil sizes.

        for iteration in range(iterations):
            nodes = list(self.graph.nodes())
            self.rng.shuffle(nodes)
            iteration_accepted = 0
            iteration_rejected = 0

            for node in nodes:
                source = partition[node]
                chosen = source
                current = best

                for target in range(self.k):
                    if target == source:
                        continue

                    source_after = counts[source] - 1
                    target_after = counts[target] + 1
                    if not (lower_size <= source_after <= upper_size):
                        continue
                    if not (lower_size <= target_after <= upper_size):
                        continue

                    partition[node] = target
                    candidate = self._objective(partition)
                    partition[node] = source

                    if candidate < current - 1e-12:
                        current = candidate
                        chosen = target
                    else:
                        iteration_rejected += 1

                if chosen != source:
                    counts[source] -= 1
                    counts[chosen] += 1
                    partition[node] = chosen
                    best = current
                    iteration_accepted += 1

            if hybrid_period and (iteration + 1) % hybrid_period == 0:
                h_accept, h_reject, best = self._two_swap(
                    partition,
                    tolerance=tolerance,
                    samples=hybrid_samples,
                    best=best,
                )
                iteration_accepted += h_accept
                iteration_rejected += h_reject

            accepted += iteration_accepted
            rejected += iteration_rejected
            trace.append(
                {
                    "iteration": iteration,
                    "weighted_cost": best,
                    "edge_cut": edge_cut(self.graph, partition),
                    "accepted": iteration_accepted,
                    "rejected": iteration_rejected,
                }
            )

        return PartitionResult(
            partition=dict(partition),
            edge_cut=edge_cut(self.graph, partition),
            weighted_cost=best,
            balance_error=balance_error(self.graph, partition, self.k),
            iterations=iterations,
            accepted_moves=accepted,
            rejected_moves=rejected,
            trace=tuple(trace),
        )

    def _two_swap(
        self,
        partition: Partition,
        *,
        tolerance: float,
        samples: int,
        best: float,
    ) -> tuple[int, int, float]:
        del tolerance  # A swap preserves every block size exactly.
        nodes = list(self.graph.nodes())
        if len(nodes) < 2:
            return 0, 0, best

        accepted = 0
        rejected = 0

        for _ in range(samples):
            u, v = self.rng.sample(nodes, 2)
            block_u = partition[u]
            block_v = partition[v]
            if block_u == block_v:
                continue

            partition[u], partition[v] = block_v, block_u
            candidate = self._objective(partition)

            if candidate < best - 1e-12:
                best = candidate
                accepted += 1
            else:
                partition[u], partition[v] = block_u, block_v
                rejected += 1

        return accepted, rejected, best
