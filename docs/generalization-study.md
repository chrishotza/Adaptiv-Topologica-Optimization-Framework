# Cross-corpus generalization study

ATOF separates **within-corpus validation** from **cross-corpus generalization**.

## Purpose

A routing policy is not established by matching an oracle on the same graph family used for training. The generalization study therefore treats each corpus as a distinct evidence layer and preserves graph-level holdout evaluation inside every corpus.

The current corpus tiers are:

| Tier | Corpus | Role |
| --- | --- | --- |
| Development | seven synthetic topology families | regression and controlled development |
| External | four standard NetworkX reference graphs | independent empirical reference surface |
| Empirical | four routine SNAP graphs | independent real-network validation |
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

The latest successful run reported macro relative regret of 1.2280 for centroid, 0.8171 for 1-NN, and 0.3242 for the majority control.

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

## Next 0.6 tier

After the aligned routine study is executed, the next research step is to run the larger SNAP scalability tier separately, then expand the number of heterogeneous unseen graphs before making stronger claims about routing generalization.

## Topology feature ablation

The reproducible ablation workflow is:

~~~bash
python -m experiments.run_feature_ablation
~~~

It preserves the same candidate strategies, objective, seeds, and leave-one-corpus-out split while changing only the topology features presented to the centroid and 1-NN routers.

The latest run found that 1-NN reached mean relative regret **0.5565** with the global-path feature family alone, compared with **0.8171** using all features. The majority control remained at **0.3242** across feature sets.

This is not used to change the public default router. The result is treated as a hypothesis for the next, larger-corpus transfer study.
