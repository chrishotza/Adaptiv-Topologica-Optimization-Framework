from __future__ import annotations
import math, random
from dataclasses import dataclass, field
from typing import Hashable, Mapping
import networkx as nx
from .partition import Partition, balance_error, edge_cut, initialize_balanced_partition, weighted_cut

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
    def __init__(self, graph: nx.Graph, k: int = 4, seed: int = 42, variant: str = "baseline") -> None:
        if k < 1: raise ValueError("k must be >= 1")
        if graph.number_of_nodes() < k: raise ValueError("k cannot exceed the number of graph nodes")
        if variant not in {"baseline", "affinity"}: raise ValueError("variant must be 'baseline' or 'affinity'")
        self.graph, self.k, self.variant = graph, k, variant
        self.rng = random.Random(seed)
        self.degree = dict(graph.degree())
    def edge_cost(self, u: Hashable, v: Hashable) -> float:
        return 1.0 if self.variant == "baseline" else 1.0 / math.sqrt(self.degree[u] * self.degree[v] + 1.0)
    def _objective(self, partition: Mapping[Hashable, int]) -> float:
        return weighted_cut(self.graph, partition, self.edge_cost)
    def refine(self, iterations: int = 25, tolerance: float = 0.05, hybrid_period: int | None = None, hybrid_samples: int = 1000) -> PartitionResult:
        if iterations < 1: raise ValueError("iterations must be >= 1")
        part = initialize_balanced_partition(self.graph, self.k)
        counts = {b: 0 for b in range(self.k)}
        for b in part.values(): counts[b] += 1
        best = self._objective(part); accepted = rejected = 0; trace=[]
        ideal = self.graph.number_of_nodes() / self.k
        for iteration in range(iterations):
            nodes=list(self.graph.nodes()); self.rng.shuffle(nodes); ia=ir=0
            for node in nodes:
                source=part[node]; chosen=source; current=best
                for target in range(self.k):
                    if target == source: continue
                    if abs(counts[source]-1-ideal) > ideal*tolerance or abs(counts[target]+1-ideal) > ideal*tolerance: continue
                    part[node]=target; candidate=self._objective(part); part[node]=source
                    if candidate < current-1e-12: current=candidate; chosen=target
                    else: ir += 1
                if chosen != source:
                    counts[source]-=1; counts[chosen]+=1; part[node]=chosen; best=current; ia+=1
            if hybrid_period and (iteration+1)%hybrid_period==0:
                ha,hr,best=self._two_swap(part, counts, tolerance, hybrid_samples, best); ia+=ha; ir+=hr
            accepted+=ia; rejected+=ir
            trace.append({"iteration":iteration,"weighted_cost":best,"edge_cut":edge_cut(self.graph,part),"accepted":ia,"rejected":ir})
        return PartitionResult(dict(part), edge_cut(self.graph,part), best, balance_error(self.graph,part,self.k), iterations, accepted, rejected, tuple(trace))
    def _two_swap(self, part: Partition, counts: dict[int,int], tolerance: float, samples: int, best: float) -> tuple[int,int,float]:
        nodes=list(self.graph.nodes()); ideal=len(nodes)/self.k; accepted=rejected=0
        for _ in range(max(0,samples)):
            u,v=self.rng.sample(nodes,2)
            bu,bv=part[u],part[v]
            if bu==bv: continue
            part[u],part[v]=bv,bu
            valid=all(abs(counts[b]-ideal)<=ideal*tolerance for b in range(self.k))
            candidate=self._objective(part) if valid else float("inf")
            if candidate < best-1e-12: best=candidate; accepted+=1
            else: part[u],part[v]=bu,bv; rejected+=1
        return accepted,rejected,best
