# Expanded 20-Graph Statistical Robustness

This is a frozen secondary analysis of workflow `35628301069`, artifact `10654092095`, from the completed 20-graph / 9-strategy transfer experiment.

## Two estimands

The primary transfer result is a **fold-balanced macro regret**: each of the four held-out corpora contributes one corpus-level mean.

This analysis also reports a **graph-weighted paired comparison** across the 20 held-out graphs. For each graph:

`delta = router_relative_regret - majority_relative_regret`

Negative delta favors the router because lower regret is better.

Uncertainty uses a percentile bootstrap over the 20 graph-level deltas with 20,000 resamples. An exact two-sided sign test is reported after removing ties.

## Key result

For `all_iqr_l2`, the protocol macro is:

- centroid: `0.1374827294`
- majority: `0.2214029079`

But with all 20 graphs equally weighted:

- centroid mean regret: `0.1705435809`
- majority mean regret: `0.1632099742`
- paired delta: `+0.0073336067`
- 95% bootstrap CI: [`-0.2487331176`, `0.2263412981`]
- graph wins/losses/ties: `3 / 5 / 12`
- exact sign-test p: `0.7265625`

Therefore the lower fold-balanced macro must **not** be described as a statistically established graph-level improvement over majority.

For `global_paths_minmax_l2`, nearest-neighbor routing has graph-weighted delta `-0.0252186484` versus majority, but its 95% bootstrap interval is [`-0.2693795219`, `0.1725282229`] and the exact sign-test p-value is `1.0`.

## Corpus pattern

For centroid `all_iqr_l2`, the macro delta versus majority by held-out corpus is:

| Corpus | Delta |
|---|---:|
| development | +0.3024924012 |
| external | +0.0123456790 |
| snap | -0.0228670022 |
| snap_scalability | -0.6276517922 |

The router's behavior therefore varies substantially by corpus family. The scalability-fold improvement is meaningful evidence for a hypothesis, but only three graphs belong to that held-out family.

## Decision

No default-router change is justified from this analysis alone.

The next experiment should test the topology regimes associated with the strong scalability-fold improvement on an independent corpus, rather than tune features against the same 20 graphs.
