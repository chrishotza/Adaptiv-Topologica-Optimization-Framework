# Topology-conditioned strategy quality routing

The fresh benchmark showed that the current centroid router can achieve low graph-level regret on the locked 20-graph corpus, but the centroid model learns only the identity of the best strategy in each training graph. It does not use the magnitude of strategy-specific quality differences.

This research layer asks a narrower question: can topology-conditioned estimates of normalized edge cut for each strategy improve on the centroid's oracle-label classification?

## Frozen protocol

For each leave-one-corpus-out fold:

- fit topology scaling on the training corpora only;
- for every strategy, keep the training graphs' normalized objective values edge_cut / edge_count;
- predict each strategy's normalized edge cut on the held-out graph using the inverse-distance weighted mean of its 3 nearest training graphs;
- rank strategies by predicted normalized edge cut;
- evaluate only the held-out graph outcomes.

The candidate router is compared against:

- the existing centroid topology router;
- majority oracle-strategy control;
- global-mean edge-cut control.

No held-out solver outcome is used during fitting.

## Why this is the next layer

The current centroid mechanism compresses a graph into an oracle class. That loses information about whether the first and second candidate strategies were nearly tied or substantially separated in the training corpus.

The quality-conditioned router keeps the strategy-specific objective surface. Its confidence signal is the relative gap between the two best predicted normalized cuts, which is available before running a solver on the held-out graph.

The output artifact reports both routing regret and confidence buckets. This creates a measurable basis for a later confidence-gated two-stage allocation policy without changing production behavior.

## Evidence boundary

This is a research-only offline replay. It does not change the public/default ATOF portfolio or router. The protocol is evaluated on a fresh execution of the existing 20-graph, k=2, 11-strategy benchmark.

