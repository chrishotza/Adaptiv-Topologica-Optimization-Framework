# Graph-level routing evaluation

ATOF treats strategy selection as a graph-level prediction problem.

## Protocol

For each graph:

1. run every candidate strategy over fixed seeds;
2. compute the graph-level oracle from mean edge cut across those seeds;
3. use only training graphs and their oracle labels to fit a topology router;
4. predict the strategy for one held-out graph;
5. evaluate that prediction against the held-out graph oracle.

Seeds of the held-out graph never participate in router training.

## Router

The reference LearnedTopologyRouter uses a transparent nearest-centroid model over topology descriptors. Feature scaling is fit from the training graphs only.

It is a baseline model, not the final meta-learning architecture.

## Metrics

- oracle agreement rate;
- mean absolute regret;
- mean relative regret;
- graph-level selected strategy;
- graph-level oracle strategy.

A topology-aware selector is only useful if it can improve or preserve performance on unseen graphs relative to non-adaptive baselines.

## Controls

Every routing experiment should include at least:

- a fixed global-strategy baseline;
- the heuristic regime selector;
- the learned topology router;
- the post-hoc oracle.

No oracle result is available to the router during prediction.
