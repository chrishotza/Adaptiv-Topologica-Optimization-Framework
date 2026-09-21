# Cross-corpus generalization study

ATOF separates **within-corpus validation** from **cross-corpus generalization**.

## Purpose

A routing policy is not established by matching an oracle on the same graph family used for training. The generalization study therefore treats each corpus as a distinct evidence layer and preserves graph-level holdout evaluation inside every corpus.

The current corpus tiers are:

| Tier | Corpus | Role |
| --- | --- | --- |
| Development | seven synthetic topology families | regression and controlled development |
| External | four standard NetworkX reference graphs | independent empirical reference surface |
| Empirical | six routine SNAP graphs | independent real-network validation |
| Scalability | ca-GrQc, ca-HepTh, Wiki-Vote | larger optional stress/generalization tier |

## Aligned study

~~~bash
python -m experiments.run_generalization_study
~~~

The aligned study executes the same two-way routing protocol over the development, external, and routine SNAP corpora and creates:

- results/generalization/latest.json
- results/generalization/routing_development.json
- results/generalization/routing_external.json
- results/generalization/routing_snap.json

The study is also available as the GitHub Actions workflow **Cross-corpus generalization validation**.

The workflow uses live SNAP downloads, preserves SHA-256 dataset provenance, and uploads the manifests as an artifact.

The larger SNAP scalability tier remains separate because its graph sizes materially change the computational regime.

## Unit of analysis

Repeated seeds are aggregated within each graph before routing evaluation.

A held-out graph contributes one routing fold. It does not contribute one training example per seed.

This distinction is critical: topology generalization is a graph-level question.

## Metrics

For each corpus ATOF can report:

- oracle agreement for the learned router;
- mean absolute regret;
- mean relative regret;
- the same metrics for the fixed global-strategy baseline;
- the same metrics for the heuristic selector.

The atof.generalization module provides two aggregate views:

- **micro** — every held-out graph receives equal weight;
- **macro** — every corpus receives equal weight.

The macro view prevents a larger corpus from silently dominating a cross-corpus summary.


### Dual-router transfer comparison

The current transfer study compares two low-complexity topology routers:

- nearest-centroid;
- 1-nearest-neighbor.

Both use the same standardized topology feature vector and differ only in how training labels are represented. This isolates whether centroid aggregation itself is contributing to transfer error.

The latest expanded 17-graph leave-one-corpus-out study reports macro relative regret of **2.6916** for centroid, **0.7744** for 1-NN, and **0.3242** for the majority control; oracle agreement is **0.4444**, **0.4603**, and **0.7381**, respectively.

## Interpretation discipline

The aggregate layer is descriptive infrastructure. It does not by itself establish universal superiority or causal benefit.

A stronger routing result requires:

1. no training leakage from held-out graphs;
2. consistent candidate strategies and objective across corpora;
3. explicit dataset provenance;
4. enough heterogeneous unseen graphs to make the generalization claim meaningful;
5. direct comparison with fixed and heuristic controls.

A combined manifest must therefore always retain the per-corpus folds and provenance instead of publishing only a single aggregate value.

## True cross-corpus transfer

The aligned study above aggregates independent within-corpus leave-one-graph-out evaluations.

A separate experiment now performs the stricter test:

~~~bash
python -m experiments.run_cross_corpus_transfer
~~~

For each test corpus, the topology router is trained only on graph-level oracle labels from the other corpora. The entire test corpus is excluded from training.

The experiment compares:

- learned topology router;
- majority-oracle strategy from the training corpora;
- transparent heuristic selector.

This is the actual leave-one-corpus-out transfer protocol. It is the appropriate next test for whether the routing signal transfers across corpus boundaries.

## Current confirmatory phase

The next phase freezes three configurations from the scaling ablation without additional tuning:

1. all features + IQR + L2;
2. global-path features + IQR + L2;
3. global-path features + min-max + L2.

The locked confirmatory workflow retains the majority control and the same 17-graph leave-one-corpus-out protocol. A parallel oracle-stability study tests whether graph-level strategy labels are themselves stable across the configured seeds. These two diagnostics are the decision gate before any further router tuning.

## Router scaling ablation

The reproducible scaling-ablation workflow is:

~~~bash
python -m experiments.run_router_scaling_ablation
~~~

It preserves the same 17-graph leave-one-corpus-out split while varying feature subsets, scaling modes, and distance metrics.

On the latest artifact, the strongest observed centroid configuration was **global-path features + IQR scaling + L2 distance**, with **0.4893** mean relative regret. The strongest observed 1-NN result in the tested family was **0.5757** with global-path features and min-max or standard-deviation scaling under L2 distance. The majority control remained at **0.3242**.

These are evidence-guiding candidates, not a public default change. They were frozen into the subsequent three-way confirmatory comparison.


## Latest expanded-corpus run

The routine SNAP corpus now contains six empirical graphs, bringing the aligned study to **17 graphs** across development, external, and SNAP tiers. GitHub Actions run **35574236663** completed successfully on commit **f603429a0c485b8c6c9692bca7c223f75cfce64e**.

The true leave-one-corpus-out macro transfer on the expanded corpus was:

| Router/control | Mean relative regret | Oracle agreement |
| --- | ---: | ---: |
| Centroid | 2.6916 | 0.4444 |
| 1-NN | 0.7744 | 0.4603 |
| Majority | 0.3242 | 0.7381 |
| Heuristic | 6.2147 | 0.0833 |

The expanded corpus confirms that 1-NN is materially more stable than the centroid router, but the majority control remains lower-regret. The 1-NN and feature-ablation studies must therefore be rerun on the expanded 17-graph corpus before selecting a public router configuration.
