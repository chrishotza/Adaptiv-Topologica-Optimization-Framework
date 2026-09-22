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

from .refinement import RefinementController


@dataclass(frozen=True)
class PartitionResult:
    partition: Partition
    edge_cut: int
    weighted_cost: float
    balance_error: float
    iterations: int
    accepted_moves: int
    rejected_moves: int
    hybrid_passes: int = 0
    hybrid_probes: int = 0
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
        self.probe_rng = random.Random(seed + 104729)
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
        hybrid_policy: str = "fixed",
        hybrid_patience: int = 2,
        hybrid_probe_samples: int = 20,
    ) -> PartitionResult:
        if iterations < 1:
            raise ValueError("iterations must be >= 1")
        if tolerance < 0:
            raise ValueError("tolerance must be >= 0")
        if hybrid_samples < 0:
            raise ValueError("hybrid_samples must be >= 0")
        if hybrid_policy not in {"fixed", "adaptive"}:
            raise ValueError("hybrid_policy must be 'fixed' or 'adaptive'")
        if hybrid_patience < 1:
            raise ValueError("hybrid_patience must be at least 1")
        if hybrid_probe_samples < 0:
            raise ValueError("hybrid_probe_samples must be >= 0")
        controller = RefinementController(
            policy=hybrid_policy,
            period=hybrid_period or max(iterations, 1),
            patience=hybrid_patience,
        )

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
            iteration_start = best
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

                    candidate = best + self._move_delta(
                        node,
                        source,
                        target,
                        partition,
                    )

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

            hybrid_triggered = False
            hybrid_probe_triggered = False
            should_hybrid = False
            if hybrid_period and controller.after_local_pass(
                iteration=iteration,
                start_cost=iteration_start,
                end_cost=best,
                tolerance=tolerance,
            ):
                should_hybrid = True
                if hybrid_policy == "adaptive":
                    hybrid_probe_triggered = True
                    controller.record_probe(iteration=iteration)
                    should_hybrid = self._probe_two_swap(
                        partition,
                        samples=hybrid_probe_samples,
                        best=best,
                    )
                if should_hybrid:
                    hybrid_triggered = True
                    hybrid_start = best
                    h_accept, h_reject, best = self._two_swap(
                        partition,
                        tolerance=tolerance,
                        samples=hybrid_samples,
                        best=best,
                    )
                    controller.record_hybrid_pass(
                        iteration=iteration,
                        start_cost=hybrid_start,
                        end_cost=best,
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
                    "hybrid": int(hybrid_triggered),
                    "hybrid_probe": int(hybrid_probe_triggered),
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
            hybrid_passes=controller.hybrid_passes,
            hybrid_probes=controller.probes,
            trace=tuple(trace),
        )

    def _move_delta(
        self,
        node: Hashable,
        source: int,
        target: int,
        partition: Mapping[Hashable, int],
    ) -> float:
        """Return the exact objective change for moving one node.

        Only edges incident to the moved node can change crossing status, so
        this computes the same weighted-cut delta as a full objective scan in
        O(deg(node)) time.
        """
        delta = 0.0
        for neighbor in self.graph.neighbors(node):
            cost = self.edge_cost(node, neighbor)
            if partition[neighbor] == source:
                delta += cost
            elif partition[neighbor] == target:
                delta -= cost
        return delta

    def _swap_delta(
        self,
        u: Hashable,
        v: Hashable,
        partition: Mapping[Hashable, int],
    ) -> float:
        """Return the exact weighted-cut change for swapping two node blocks.

        Only edges incident to ``u`` or ``v`` can change crossing status. The
        direct ``u-v`` edge, when present, remains crossing because the two
        nodes exchange distinct blocks, so it contributes zero and is skipped.
        """
        block_u = partition[u]
        block_v = partition[v]
        delta = 0.0

        for neighbor in self.graph.neighbors(u):
            if neighbor == v:
                continue
            cost = self.edge_cost(u, neighbor)
            old_cross = partition[neighbor] != block_u
            new_cross = partition[neighbor] != block_v
            delta += cost * (int(new_cross) - int(old_cross))

        for neighbor in self.graph.neighbors(v):
            if neighbor == u:
                continue
            cost = self.edge_cost(v, neighbor)
            old_cross = partition[neighbor] != block_v
            new_cross = partition[neighbor] != block_u
            delta += cost * (int(new_cross) - int(old_cross))

        return delta

    def _probe_two_swap(
        self,
        partition: Partition,
        *,
        samples: int,
        best: float,
    ) -> bool:
        """Return whether a boundary-aware sampled swap finds an improvement."""
        if samples <= 0:
            return False

        boundary = [
            node
            for node in self.graph.nodes()
            if any(partition[neighbor] != partition[node] for neighbor in self.graph.neighbors(node))
        ]
        candidates = boundary if len(boundary) >= 2 else list(self.graph.nodes())
        by_block: dict[int, list[Hashable]] = {}
        for node in candidates:
            by_block.setdefault(partition[node], []).append(node)

        blocks = list(by_block)
        if len(blocks) < 2:
            return False

        for _ in range(samples):
            block_u, block_v = self.probe_rng.sample(blocks, 2)
            u = self.probe_rng.choice(by_block[block_u])
            v = self.probe_rng.choice(by_block[block_v])
            if best + self._swap_delta(u, v, partition) < best - 1e-12:
                return True
        return False

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

            candidate = best + self._swap_delta(u, v, partition)

            if candidate < best - 1e-12:
                partition[u], partition[v] = block_v, block_u
                best = candidate
                accepted += 1
            else:
                rejected += 1

        return accepted, rejected, best
