# Online selector hierarchical fusion

PR #104 showed that a topology-local predictor alone misses the strongest held-out positive opportunity (ca_grqc) and reduces probing to one graph.

This follow-up diagnostic tests a hierarchical fusion: the global pair-median prediction is combined with local pair evidence using a fixed neighbor-radius gate.

Both gate orientations are evaluated:
- global_near: trust global evidence when the local neighborhood is close;
- local_near: trust local evidence when the local neighborhood is close.

Fixed k values are 3, 5, 7 and fixed radius thresholds are 5, 7.5, 10, 12.5, 15, 20 in the frozen router distance units.

This is diagnostic only. No cell is selected automatically and production/default behavior is unchanged.
