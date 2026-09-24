# Seed-stability stratified routing calibration

This research layer follows the cross-seed calibration result by separating two questions:

1. does the held-out graph have the same strategy oracle across all three seeds?
2. does the topology router behave differently on stable versus unstable graphs?

It compares two graph-level training targets without changing the router geometry:

- **mean oracle**: strategy with the lowest mean edge cut across the three training seeds;
- **modal oracle**: strategy that is the per-seed oracle most often across the three training seeds, with deterministic lexical tie-breaking.

Each corpus fold derives both targets from training graphs only. Held-out evaluation is performed against each held-out seed oracle. Confidence intervals are graph-level.

The artifact also reports oracle concentration, the stable/unstable stratification, and the paired difference between the two target definitions.

No target is promoted automatically and no public/default behavior changes.
