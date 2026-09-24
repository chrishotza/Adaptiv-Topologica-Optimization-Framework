# k=8 routing generalization

This experiment extends the validated k=4 routing-generalization protocol to 8-way graph partitioning.

## Frozen protocol

- 20-graph expanded corpus.
- k=8.
- Candidate strategies: BLOC, BLOC-affinity, METIS, KaHIP, KaMinPar, KaMinPar-strong, Mt-KaHyPar, and Mt-KaHyPar-quality.
- Three fixed solver seeds: 42, 101, 2024.
- Same 11-feature topology representation.
- IQR-scaled L2 routing.
- Leave-one-corpus-out evaluation.
- Graph-level mean relative regret against the graph-specific mean edge-cut oracle.
- No production/default ATOF behavior changes.

The experiment is evidence about routing transfer at k=8, not a claim of universal solver dominance.
