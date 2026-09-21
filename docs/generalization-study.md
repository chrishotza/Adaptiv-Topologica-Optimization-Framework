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

The `atof.generalization` module provides two aggregate views:

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

## Recommended 0.6 experiment

The next empirical milestone is to execute the same two-way protocol across the development, external, and routine SNAP corpora, then run the larger SNAP scalability tier separately.

The report should preserve:

- repository commit SHA;
- dataset SHA-256 where downloads are involved;
- Python and NetworkX versions;
- graph sizes;
- seeds and iteration count;
- per-graph routing folds;
- micro and macro aggregates.

A single aggregate number should never replace the per-corpus and per-graph evidence.
