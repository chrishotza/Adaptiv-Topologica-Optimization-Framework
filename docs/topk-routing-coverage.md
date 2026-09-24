# Top-k routing coverage and portfolio ceiling

The previous seed-stability experiments found that 7 of 20 graphs have different per-seed oracle strategies. This layer asks whether that instability is visible in the topology router's ranked candidate list.

For each corpus leave-one-out fold:

- the router is trained on graph-level mean-oracle labels from training graphs only;
- each held-out graph receives a topology-only full strategy ranking;
- evaluation is repeated for all three held-out seeds;
- top-1, top-2, and top-3 report whether the per-seed oracle appears inside the ranked candidate set;
- best-of-k relative regret measures the ceiling obtained if one could evaluate all k candidates and then select the best using hindsight.

The best-of-k quantity is explicitly an analysis ceiling, not a deployable policy. Runtime is reported separately using the measured runtime of the k ranked candidates.

Results are stratified by seed-stable versus seed-unstable held-out graphs. No production/default policy changes.
