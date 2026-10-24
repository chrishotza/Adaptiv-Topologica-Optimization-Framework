from __future__ import annotations

import math

import networkx as nx

from .partition import (
    Partition,
    balance_error,
    edge_cut,
    initialize_balanced_partition,
)
from .strategies import BLOCReloc, PartitionResult


class SoftBalanceReloc(BLOCReloc):
    """Research-only BLOC-RELOC variant with temporary soft balance."""

    def refine(
        self,
        iterations: int = 25,
        balance_slack: int = 1,
        balance_penalty: float = 0.5,
        hybrid_period: int | None = None,
        hybrid_samples: int = 100,
    ) -> PartitionResult:
        if iterations < 1:
            raise ValueError("iterations must be at least 1")
        if balance_slack < 0:
            raise ValueError("balance_slack must be >= 0")
        if balance_penalty < 0:
            raise ValueError("balance_penalty must be >= 0")
        if hybrid_period is not None and hybrid_period < 1:
            raise ValueError("hybrid_period must be at least 1")
        if hybrid_samples < 0:
            raise ValueError("hybrid_samples must be >= 0")

        partition = initialize_balanced_partition(self.graph, self.k)
        counts = {block: 0 for block in range(self.k)}
        for block in partition.values():
            counts[block] += 1

        n = self.graph.number_of_nodes()
        lower_size = n // self.k
        upper_size = math.ceil(n / self.k)
        soft_lower = lower_size - balance_slack
        soft_upper = upper_size + balance_slack

        best = self._objective(partition)
        search_penalty = self._balance_penalty(
            counts, lower_size=lower_size, upper_size=upper_size
        )
        search_score = best + balance_penalty * search_penalty

        accepted = 0
        rejected = 0
        hybrid_passes = 0
        hybrid_accepted = 0
        hybrid_rejected = 0
        trace: list[dict[str, float | int]] = []

        for iteration in range(iterations):
            nodes = list(self.graph.nodes())
            self.rng.shuffle(nodes)
            iteration_accepted = 0
            iteration_rejected = 0

            for node in nodes:
                source = partition[node]
                chosen = source
                current = best
                current_score = search_score

                for target in range(self.k):
                    if target == source:
                        continue

                    source_after = counts[source] - 1
                    target_after = counts[target] + 1
                    if not (soft_lower <= source_after <= soft_upper):
                        continue
                    if not (soft_lower <= target_after <= soft_upper):
                        continue

                    candidate = best + self._move_delta(
                        node,
                        source,
                        target,
                        partition,
                    )
                    candidate_penalty = (
                        search_penalty
                        - self._block_penalty(
                            counts[source], lower_size, upper_size
                        )
                        - self._block_penalty(
                            counts[target], lower_size, upper_size
                        )
                        + self._block_penalty(
                            source_after, lower_size, upper_size
                        )
                        + self._block_penalty(
                            target_after, lower_size, upper_size
                        )
                    )
                    candidate_score = candidate + balance_penalty * candidate_penalty

                    if candidate_score < current_score - 1e-12:
                        current = candidate
                        current_score = candidate_score
                        chosen = target
                    else:
                        iteration_rejected += 1

                if chosen != source:
                    counts[source] -= 1
                    counts[chosen] += 1
                    partition[node] = chosen
                    best = current
                    search_score = current_score
                    search_penalty = self._balance_penalty(
                        counts, lower_size=lower_size, upper_size=upper_size
                    )
                    iteration_accepted += 1

            accepted += iteration_accepted
            rejected += iteration_rejected

            hybrid_triggered = 0
            if hybrid_period and (iteration + 1) % hybrid_period == 0:
                repair_count, best = self._repair(
                    partition,
                    counts,
                    best,
                    lower_size=lower_size,
                    upper_size=upper_size,
                )
                accepted += repair_count
                search_penalty = self._balance_penalty(
                    counts,
                    lower_size=lower_size,
                    upper_size=upper_size,
                )
                search_score = best

                h_accept, h_reject, best = self._two_swap(
                    partition,
                    tolerance=0.0,
                    samples=hybrid_samples,
                    best=best,
                )
                hybrid_passes += 1
                hybrid_accepted += h_accept
                hybrid_rejected += h_reject
                accepted += h_accept
                rejected += h_reject
                hybrid_triggered = 1

            trace.append(
                {
                    "iteration": iteration,
                    "weighted_cost": best,
                    "edge_cut": edge_cut(self.graph, partition),
                    "balance_error": balance_error(self.graph, partition, self.k),
                    "balance_penalty": search_penalty,
                    "accepted": iteration_accepted,
                    "rejected": iteration_rejected,
                    "hybrid": hybrid_triggered,
                }
            )

        repair_accepted, best = self._repair(
            partition,
            counts,
            best,
            lower_size=lower_size,
            upper_size=upper_size,
        )
        accepted += repair_accepted

        return PartitionResult(
            partition=dict(partition),
            edge_cut=edge_cut(self.graph, partition),
            weighted_cost=best,
            balance_error=balance_error(self.graph, partition, self.k),
            iterations=iterations,
            accepted_moves=accepted,
            rejected_moves=rejected,
            hybrid_passes=hybrid_passes,
            hybrid_probes=0,
            trace=tuple(trace),
        )

    @staticmethod
    def _block_penalty(size: int, lower_size: int, upper_size: int) -> float:
        if size < lower_size:
            return float((lower_size - size) ** 2)
        if size > upper_size:
            return float((size - upper_size) ** 2)
        return 0.0

    def _balance_penalty(
        self,
        counts: dict[int, int],
        *,
        lower_size: int,
        upper_size: int,
    ) -> float:
        return sum(
            self._block_penalty(size, lower_size, upper_size)
            for size in counts.values()
        )

    def _repair(
        self,
        partition: Partition,
        counts: dict[int, int],
        best: float,
        *,
        lower_size: int,
        upper_size: int,
    ) -> tuple[int, float]:
        accepted = 0

        while True:
            oversized = [b for b, size in counts.items() if size > upper_size]
            undersized = [b for b, size in counts.items() if size < lower_size]
            if not oversized or not undersized:
                return accepted, best

            best_move: tuple[float, object, int, int] | None = None
            for source in oversized:
                for node in self.graph.nodes():
                    if partition[node] != source:
                        continue
                    for target in undersized:
                        candidate = best + self._move_delta(
                            node, source, target, partition
                        )
                        if best_move is None or candidate < best_move[0]:
                            best_move = (candidate, node, source, target)

            if best_move is None:
                return accepted, best

            candidate, node, source, target = best_move
            partition[node] = target
            counts[source] -= 1
            counts[target] += 1
            best = candidate
            accepted += 1

