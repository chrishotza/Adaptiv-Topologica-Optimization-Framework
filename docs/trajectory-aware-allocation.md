# Trajectory-aware solver allocation research

This layer sits above the mature external solver portfolio and evaluates whether topology priors can be converted into a bounded sequential allocation policy without changing ATOF's public/default behavior.

## Experimental object

The benchmark replays the already-measured 20-graph, k=2, 11-strategy surface from the fresh SOTA protocol. Each held-out graph is treated as a sequence of solver actions:

1. Rank candidate strategies from a topology-only centroid router fitted on the other corpora.
2. Estimate action cost from the training corpora using the median runtime per edge for each strategy.
3. Execute the first ranked action.
4. Reveal its measured edge cut and runtime.
5. Continue to the next ranked action only when the training-only predicted budget permits it.
6. Stop after a non-material improvement or budget exhaustion.
7. Return the best observed edge cut among actions actually replayed.

The replay is deliberately offline. The measured test runtime is reported as an outcome; budget feasibility is decided before execution from training-only cost estimates.

## Frozen policy gate

The confirmatory policy is frozen before inspecting held-out results:

- topology router: centroid;
- scaling: IQR;
- metric: L2;
- budget factors: 1x, 2x, 3x the predicted cost of the first-ranked strategy;
- minimum relative improvement to continue: 1%.

The 1x case is equivalent to the single-shot router. The 2x and 3x cases test bounded sequential allocation.

## Leakage boundary

No held-out graph is used to fit topology centroids, feature scaling, or runtime-cost coefficients. Solver outcomes from the held-out graph are only consumed after their corresponding action is selected by the frozen ranking.

The experiment does not use graph-level oracle labels for control decisions, and it does not modify the production portfolio selector.

## What the artifact measures

The output includes:

- relative regret against the graph-level oracle;
- actual cumulative runtime of executed actions;
- number of solver actions per graph;
- selected strategy and observed strategy sequence;
- paired bootstrap confidence intervals for controller vs single-shot centroid routing;
- the same paired comparisons for the 1x/2x/3x budget scenarios.

This is a research gate, not a claim that sequential allocation is superior. The purpose is to establish a reproducible evidence surface for the next controller iteration.
