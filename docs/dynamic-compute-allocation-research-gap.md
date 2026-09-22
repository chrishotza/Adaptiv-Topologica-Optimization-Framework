# Dynamic compute allocation — research gap

## Motivation

The 2026 learned-coarsening work on Mt-KaHyPar reports that guided coarsening can improve quality while adding runtime overhead. The paper explicitly notes that a portfolio approach could selectively enable guided coarsening on instances where it is likely to yield substantial quality improvements.

This makes a simple claim such as 'ATOF uses an intelligent router' insufficiently differentiated. The relevant research question is narrower:

> Can an online controller allocate a finite search budget among complementary partitioning neighborhoods or solver components using observed marginal return, while preserving solution quality?

## Difference from static solver selection

A static router answers:

- Which solver or strategy should be used for this graph?

A dynamic compute allocator answers:

- Given the computation already spent on this graph, what should be executed next?

The second problem is sequential. Its state includes current objective, recent gain, estimated work, stagnation, and evidence from cheap probes. A decision is valuable only if the additional improvement justifies its compute cost.

## Proposed controlled study

Use the same graph-level corpus and objective while comparing:

1. fixed local refinement budget;
2. fixed local + fixed hybrid budget;
3. current safe adaptive controller;
4. a marginal-return controller that estimates gain/work from the preceding interventions;
5. an offline hindsight oracle that selects the best next intervention using the full recorded trajectory.

The hindsight oracle is not a production method. It defines an upper reference for how much value remains in dynamic allocation if decisions were made with perfect future information.

## Primary metrics

Measure the quality-versus-compute curve, not only the final endpoint:

### Structural work unit

ATOF now records a machine-independent work proxy for the two principal local-search operators:

- local node-move work counts edge-incidence traversals performed while evaluating feasible moves;
- hybrid two-swap work counts the corresponding edge incidences inspected for each sampled swap;
- both are therefore reported in the same structural work unit rather than treating the number of random samples as equivalent computation.

The trace records gain, work, and gain-per-work for each iteration. Wall-clock time remains a separate, machine-specific measure and is not replaced by this proxy.



- edge cut at fixed time budgets;
- relative regret at equal compute;
- area under the quality-vs-time curve;
- number of instances improved / tied / regressed;
- worst per-instance regression;
- hybrid/local work ratio;
- additional quality per unit of structural work.

Use paired graph-level comparisons with identical seeds and graph order. Preserve CPU model, thread count, package versions, and dataset hashes.

## Required baselines

The dynamic allocator must be compared against mature static solvers, not only BLOC-RELOC variants:

- METIS;
- KaHIP;
- KaMinPar;
- Mt-KaHyPar;
- the SEA 2026 learned-coarsening implementation when reproducibly available.

NetworkX Kernighan-Lin remains useful as a classical two-way control but should not be the only external reference.

## Safety criterion

No dynamic policy should become a public default because of an average improvement alone. The promotion gate should require:

- no unexplained per-instance regression on the locked corpus;
- explicit behavior under compute truncation;
- graph-level holdout evaluation;
- reproducible seeds and provenance;
- a statistically supported quality-versus-compute improvement against the strongest matched baseline.

## Current evidence boundary

ATOF does not yet satisfy those conditions. The current credit-routing experiment was therefore kept out of main after observing individual quality regressions despite meaningful compute savings. The current state-of-art benchmark is intended to establish the stronger external baseline before revisiting dynamic allocation.

## Reference

Schrape et al., SEA 2026, 'Engineering Learned Heuristics to Improve Clustering for Multilevel Graph Partitioning': https://doi.org/10.4230/LIPIcs.SEA.2026.25