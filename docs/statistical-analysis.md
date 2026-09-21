# Statistical analysis layer

ATOF separates descriptive analysis from inferential claims.

## Graph-aware paired comparisons

The public statistical layer aggregates repeated seeds **within each graph** before comparing strategies. For a pair A/B, the primary difference is:

D_g = mean_seed(metric(A, g)) - mean_seed(metric(B, g))

This preserves the graph as the resampling unit instead of treating repeated seeds as independent graphs.

Run it with:

~~~bash
python -m experiments.run_statistical_analysis
~~~

The runner compares BLOC-RELOC affinity against the random balanced baseline, BLOC-RELOC baseline against random balanced, affinity against baseline, and affinity against NetworkX Kernighan-Lin for the canonical two-way protocol.

## Bootstrap uncertainty

bootstrap_mean_ci() performs a deterministic percentile bootstrap of the graph-level differences. The default is 5,000 resamples and a 95% interval.

A negative mean difference means strategy A has a lower value of the reported metric than strategy B. For unweighted edge cut, lower is the better direction of the metric itself.

The summary also reports graph-level wins, losses, ties, and a standardized paired effect based on the standard deviation of the graph-level differences.

These are uncertainty and effect summaries, not a universal significance claim.

## Activity persistence

The observatory records whether each optimization iteration has at least one accepted move.

From that trace we calculate active-iteration count, activity fraction, extinction iteration, time to 25%, 50%, and 75% of cumulative accepted moves, and an aggregated persistence curve.

The persistence curve is:

S(t) = (# traces with accepted activity at t or later) / (# traces)

It is a descriptive empirical curve. The current implementation does not fit a Kaplan-Meier estimator or a hazard model.

## Regime comparisons

compare_by_regime() groups benchmark rows by the topology regime already produced by the selector and reports arithmetic means for final edge cut, relative weighted-objective improvement, acceptance rate, and extinction iteration.

These summaries are intended for exploration and visualization.

## Correlation

pearson_correlation() provides a transparent exploratory Pearson coefficient for numeric row fields.

Correlation does not establish causation.

## Scope and limitations

The seven-graph suite is synthetic and developmental. Its bootstrap interval quantifies uncertainty within this suite; it does not establish population-level generalization to unseen real-world graph corpora.

The initial statistical runner does not apply multiplicity correction. Stronger external datasets, prespecified comparison families, and hierarchical or paired inferential methods should be added before making broad generalization claims.

Historical BLOC-RELOC correlations remain exploratory evidence and should not be mixed with fresh public benchmark results without protocol metadata.
