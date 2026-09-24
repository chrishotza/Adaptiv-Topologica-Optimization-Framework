# Confidence-gate sensitivity matrix

The confidence-gated allocation experiment at the frozen reference setting uses a 2x predicted-runtime budget and the training-only median confidence threshold.

This research layer deliberately does not choose a new production policy. It measures a fixed sensitivity matrix:

- confidence threshold quantiles: 25%, 50%, 75%;
- predicted-runtime budget factors: 1x, 1.5x, 2x, 3x.

For every cell, threshold estimation remains nested inside the training corpus through leave-one-graph-out topology fits. The held-out corpus is evaluated only after the policy parameters for that fold have been derived.

The artifact reports all 12 cells, including regret delta against single-shot centroid routing, bootstrap confidence interval, runtime overhead, probe rate, and action count.

The purpose is to determine whether the small effect observed by the frozen reference policy is stable across nearby parameter choices or concentrated in one setting. The matrix is exploratory; no cell is promoted automatically.
