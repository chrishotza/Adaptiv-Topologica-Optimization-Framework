# Methodology

ATOF treats graph partitioning as an optimization problem whose useful evaluation depends on an explicit objective and explicit constraints.

## Canonical public objective

The BLOC-RELOC baseline minimizes the number of crossing edges:

`cut(G,P) = |{(u,v) in E : P(u) != P(v)}|`

The affinity variant uses the edge contribution

`w(u,v) = 1 / sqrt(deg(u) deg(v) + 1)`

for exploratory degree-aware refinement.

These objectives are intentionally exposed separately. A lower weighted objective is not automatically evidence of a lower unweighted edge cut.

## Balance constraint

The public implementation uses node-count balance as a constraint during local moves. The configured tolerance is recorded with each experiment.

## Regime detection

Topology descriptors are used to characterize structure. The included selector is a transparent heuristic baseline, not a claim of universal optimality.

## Benchmark discipline

A benchmark is considered interpretable only when its:

- algorithms are identified precisely;
- objective is fixed;
- dataset scope is stated;
- seeds are stated;
- implementation commit is known;
- results are stored separately from exploratory artifacts.

This is the standard the public repository will use for future benchmark releases.
