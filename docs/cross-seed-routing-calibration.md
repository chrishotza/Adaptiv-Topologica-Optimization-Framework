# Cross-seed routing calibration

This research layer asks whether the strategy oracle is stable across repeated solver seeds and whether a topology router trained on seed-expanded labels changes held-out regret.

The fresh benchmark contains 20 graphs, 11 strategies, and three fixed seeds per graph. The standard topology router receives one oracle label per training graph, based on mean edge cut across the three training seeds.

The second research-only router keeps the topology features and distance rule frozen (all routing features, IQR scaling, L2 distance) but expands the training labels to one oracle strategy per seed. The predictor still observes topology only and does not receive the held-out seed. Seed-expanded training duplicates the topology vector once per observed training seed while retaining that seed's oracle label.

All three seeds of a held-out graph are excluded from that fold's training data. Held-out evaluation is performed at the graph-seed level, then bootstrap confidence intervals aggregate the three seeds within each graph before resampling.

The artifact reports:
- graph-level router relative regret against the per-seed oracle;
- seed-expanded router relative regret against the per-seed oracle;
- paired graph-level regret delta;
- per-graph seed-oracle instability;
- agreement between the graph-level prediction and each seed's oracle.

This is a calibration study. It does not select a production policy and does not make a solver-superiority claim.
