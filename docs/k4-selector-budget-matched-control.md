# K=4 budget-matched selector control

The merged k=4 online selector spends a second solver action on a subset of graphs. A key control is whether the observed gain comes from the selector's timing decision or merely from having extra solver budget.

This control therefore keeps fixed:

- k=4
- the same 20-graph corpus
- the same eight strategies
- the same IQR/L2 router
- the same five solver seeds
- the same predicted rank-2/rank-3 alternate
- the same number of probed graphs in every held-out corpus

The only difference is the probe decision: the control selects the same number of test graphs uniformly at random within each held-out corpus.

The random allocation is repeated 500 times with deterministic seeds. Results are reported as graph-level paired selector-minus-random deltas, plus the random-control distribution.

No held-out oracle is used for allocation, and no production/default ATOF behavior changes.
