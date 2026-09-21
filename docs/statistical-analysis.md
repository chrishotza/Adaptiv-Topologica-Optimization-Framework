# Statistical analysis layer

ATOF separates descriptive analysis from inferential claims.

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

Correlation does not establish causation. Repeated seeds are not automatically independent observations of topology. Future inferential analysis should therefore use graph-aware resampling or hierarchical methods rather than treating every seed as a fully independent graph.

## Statistical upgrade path

The research-grade next layer should add:

1. graph-level train/test separation for learned selectors;
2. paired comparisons on the same graph and seed;
3. graph-level bootstrap confidence intervals;
4. effect sizes with uncertainty;
5. preregistered multiple-comparison handling;
6. optional survival/hazard models only when censoring semantics are explicitly defined.

Historical BLOC-RELOC correlations remain exploratory evidence and should not be mixed with fresh public benchmark results without protocol metadata.
