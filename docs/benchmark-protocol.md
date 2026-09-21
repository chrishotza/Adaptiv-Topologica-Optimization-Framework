# Canonical benchmark protocol

The canonical benchmark is intentionally conservative.

## Graph suite

The initial development suite contains deterministic synthetic graphs representing:

- path;
- cycle;
- grid;
- Erdős–Rényi;
- Barabási–Albert;
- Watts–Strogatz;
- stochastic block structure.

These graphs are generated directly by NetworkX from fixed seeds. They are a development suite, not a substitute for external real-world datasets.

## Compared strategies

The initial protocol compares:

1. round-robin balanced assignment;
2. random balanced assignment;
3. BLOC-RELOC baseline;
4. BLOC-RELOC degree-affinity;
5. deterministic spectral bisection using the Fiedler vector for a 2-way partition;
6. NetworkX Kernighan–Lin for a 2-way partition.

The names describe the actual implementations used. No method is labeled “SOTA” or “Louvain” unless the corresponding implementation is actually being run.

## Primary metric

The cross-strategy metric is unweighted edge cut:

cut(G,P) = |{(u,v) in E : P(u) != P(v)}|

Lower values mean fewer crossing edges for the same graph, k, and balance constraint.

The degree-affinity objective is reported separately because weighted cost is not directly interchangeable with unweighted edge cut.

## Repeated runs

Every stochastic strategy is executed over multiple fixed seeds. Results are stored as raw rows rather than only as a single aggregate score.

## Reproducibility

Each benchmark artifact records:

- Python version;
- NetworkX version;
- platform;
- graph sizes;
- k;
- seeds;
- iterations;
- objective;
- generation timestamp.

For a research release, the benchmark should additionally record the repository commit SHA and exact dataset provenance.

## What this benchmark does not establish

A small synthetic suite cannot establish general superiority over graph-partitioning literature. It is the canonical regression and development benchmark for the public implementation.

External datasets, stronger baselines, solver versions, statistical tests, and ablations should be added in later benchmark releases without changing the interpretation of this initial suite.


## Spectral reference baseline

The spectral baseline constructs the unnormalized graph Laplacian, computes its second eigenvector, orders nodes by that Fiedler coordinate, and assigns the ordered nodes to two balanced blocks.

The public implementation uses NumPy only and a dense eigensolver. To avoid silently turning the reference baseline into a scalability bottleneck, it is limited to graphs with at most 2000 nodes.

This is an interpretable classical reference baseline. It is not presented as a state-of-the-art partitioner and is not included in the larger SNAP scalability tier.
