# External reference validation

ATOF 0.4.0 adds a small external-reference layer that reuses the canonical two-way benchmark protocol on standard empirical graphs exposed by NetworkX.

## Corpus

The current corpus contains:

- **Karate Club** — Zachary's social network.
- **Davis Southern Women** — an empirical bipartite social network.
- **Florentine Families** — historical family relationship network.
- **Les Misérables** — character coappearance network.

Each dataset is loaded through a named GraphDataset entry with explicit source and reference metadata. The loader normalizes graphs to simple undirected graphs and removes self-loops. The benchmark does not use node labels or semantic annotations.

NetworkX documents these as standard graph generators/reference datasets. The exact source URLs are stored in src/atof/datasets.py and in the generated result artifact.

## Protocol

For each graph and fixed seed, the benchmark evaluates:

1. balanced round-robin assignment;
2. balanced random assignment;
3. BLOC-RELOC baseline;
4. BLOC-RELOC degree-affinity;
5. NetworkX Kernighan-Lin.

The primary cross-strategy metric is unweighted edge cut. For datasets with edge weights, weights are deliberately ignored so that the comparison remains on one common metric.

The experiment also performs leave-one-graph-out routing. The held-out graph contributes neither topology features nor benchmark outcomes to router training.

## Statistical layer

Repeated seeds are first averaged within graph. Bootstrap resampling then occurs over graphs, preserving the graph as the generalization unit.

The default external experiment reports 5,000 percentile-bootstrap resamples with a 95% interval.

## Interpretation

This layer is stronger than the synthetic development suite because the graphs are empirical reference graphs rather than generated topology families. It is still **not** evidence of universal generalization:

- the corpus contains only four small graphs;
- the graphs are not a random sample of real-world graphs;
- the routing training set contains only three graphs per fold;
- the benchmark objective is limited to unweighted edge cut.

The correct interpretation is: **ATOF now has a reproducible external-reference test surface on which topology-aware routing and optimization behavior can be compared without silently mixing historical results with fresh synthetic development results.**

## Run

~~~bash
python -m experiments.run_external_validation
~~~

The result is written to:

~~~text
results/external/latest.json
~~~

The artifact includes environment metadata, commit provenance, dataset provenance, raw benchmark rows, graph-level paired comparisons, and routing folds.
