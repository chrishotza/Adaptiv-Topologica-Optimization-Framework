# Confidence-gated two-stage allocation

This research layer tests whether the centroid router's topology distance can be used as a pre-execution uncertainty signal to decide when to spend a second solver evaluation.

## Frozen policy

For each leave-one-corpus-out fold:

1. Fit the centroid topology router on the training corpora only.
2. Estimate a confidence-margin threshold from the training corpus using inner leave-one-graph-out centroid fits and the median (50th percentile) of the observed margins.
3. Run the first-ranked strategy on the held-out graph.
4. Probe the second-ranked strategy only when the held-out graph's centroid margin is below the training-derived threshold and the training-only predicted runtime of the two actions fits within 2x the first action's predicted runtime.
5. Return the best observed edge cut.

The second action is therefore gated before any held-out outcome is observed.

## Evidence boundary

This is research-only offline replay. It does not alter ATOF's public/default portfolio or routing behavior.
