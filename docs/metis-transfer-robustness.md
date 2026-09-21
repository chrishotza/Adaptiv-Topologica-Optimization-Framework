# METIS 7→8 strategy statistical robustness

This note records a paired graph-level robustness analysis of the locked seven-strategy and eight-strategy leave-one-corpus-out experiments. The only candidate-space change is the addition of `metis_multilevel_balanced`.

## Paired result

Each of the 17 held-out graphs is paired between the seven-strategy and eight-strategy artifacts. The delta is **new relative regret − old relative regret**; negative values indicate lower regret after adding METIS.

| Configuration | Router | Old graph mean | New graph mean | Mean delta | Improved / worsened | Exact sign-flip p |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `all_iqr_l2` | centroid | 0.7797 | 0.3833 | -0.3964 | 5 / 2 | 0.054688 |
| `all_iqr_l2` | 1-NN | 0.6835 | 0.0885 | -0.5950 | 9 / 3 | 0.002930 |
| `global_paths_iqr_l2` | centroid | 0.5629 | 0.4076 | -0.1553 | 3 / 4 | 0.453125 |
| `global_paths_iqr_l2` | 1-NN | 0.7120 | 0.0919 | -0.6201 | 9 / 4 | 0.003784 |
| `global_paths_minmax_l2` | centroid | 0.6662 | 0.4076 | -0.2586 | 4 / 4 | 0.289062 |
| `global_paths_minmax_l2` | 1-NN | 0.6639 | 0.0908 | -0.5731 | 8 / 4 | 0.007568 |

Bootstrap 95% intervals for the 1-NN mean delta are, respectively, [-1.1351, -0.1517], [-1.1539, -0.1757], and [-1.1155, -0.1222], using 20,000 deterministic resamples.

## What the robustness check says

The strongest and most consistent effect is for **1-NN**. Across all three locked configurations, adding METIS lowers graph-level relative regret by roughly 0.57–0.62, with 8–9 of 17 graphs improving and exact one-sided sign-flip p-values below 0.01.

The centroid router moves in the same direction in all three configurations, but the paired evidence is weaker on this 17-graph corpus: only `all_iqr_l2` is near the conventional 0.05 threshold, while the two global-path comparisons remain compatible with zero under the sign-flip test.

For the new eight-strategy candidate space, the macro corpus-level relative regret is 0.3103–0.3448 for centroid and 0.0900–0.0927 for 1-NN across the three locked configurations, versus 0.3787 for the mandatory majority control.

## Expanded oracle

The eight-strategy oracle distribution is:

| Corpus | Oracle distribution |
| --- | --- |
| Development (7) | METIS 6; Kernighan-Lin 1 |
| External (4) | METIS 1; Kernighan-Lin 2; BLOC-RELOC baseline 1 |
| SNAP (6) | Kernighan-Lin 5; METIS 1 |

Thus METIS materially changes the oracle labels instead of merely duplicating the prior seven-strategy space.

## Interpretation boundary

This is a paired robustness analysis over the **17 graphs already in the study**, not a population inference over arbitrary graphs. Corpus membership creates dependence structure, so the p-values are best treated as sensitivity/robustness statistics rather than a definitive universal hypothesis test.

The majority control remains mandatory in the underlying experiments. Its regret changes when the oracle changes, so it is not used as the primary paired endpoint for the seven-to-eight candidate-space comparison.

The public/default router is unchanged by this analysis.

## Provenance

- Seven-strategy confirmatory artifact: run **35580437557**, artifact **10630387720**, SHA-256 `edfeac72be0bc066c70f549fd07c53bb1b94adbd173c2922de45cd4a45286dd3`.
- Eight-strategy METIS confirmatory artifact: run **35584123689**, artifact **10632280359**, SHA-256 `2344b22654a3c91ccaa13bb2e9660bdf7732b2f3b6a89fbcfb841d1806544d5c`.
- Seeds: 42, 101, 2024.
- `k=2`, 25 BLOC-RELOC refinement iterations.
