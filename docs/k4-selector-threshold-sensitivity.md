# K=4 selector threshold sensitivity

This study tests whether the observed k=4 oracle-free online selector effect is sensitive to how much predicted benefit is required before spending a second solver action.

The protocol is otherwise frozen:

- k=4
- 20-graph expanded corpus
- eight candidate strategies
- IQR/L2 topology router
- five fixed seeds: 7, 42, 101, 2024, 8191
- leave-one-corpus-out training
- rank-2/rank-3 alternate prediction from training-only ordered-pair medians
- maximum two solver actions per seed

The fixed trigger thresholds are:

- 0.0000
- 0.0025
- 0.0050
- 0.0100
- 0.0200

A threshold of 0 reproduces the merged selector protocol. Positive thresholds require a larger predicted relative edge-cut improvement before the alternate is probed.

Each threshold is evaluated independently. No threshold is selected automatically from held-out results. The study reports graph-level paired deltas versus top-1, bootstrap confidence intervals, probe rate, mean actions, and runtime.

This is sensitivity evidence, not a production tuning change.
