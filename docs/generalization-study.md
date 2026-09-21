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

## Interpretation discipline

The aggregate layer is descriptive infrastructure. It does not by itself establish universal superiority or causal benefit.

A stronger routing result requires:

1. no training leakage from held-out graphs;
2. consistent candidate strategies and objective across corpora;
3. explicit dataset provenance;
4. enough heterogeneous unseen graphs to make the generalization claim meaningful;
5. direct comparison with fixed and heuristic controls.

A combined manifest must therefore always retain the per-corpus folds and provenance instead of publishing only a single aggregate value.

## Next 0.6 tier

After the aligned routine study is executed, the next research step is to run the larger SNAP scalability tier separately, then expand the number of heterogeneous unseen graphs before making stronger claims about routing generalization.
