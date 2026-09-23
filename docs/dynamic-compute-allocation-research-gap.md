# Dynamic compute allocation — research gap

## Motivation

The 2026 learned-coarsening work on Mt-KaHyPar reports that guided coarsening can improve quality while adding runtime overhead. The paper explicitly notes that a portfolio approach could selectively enable guided coarsening on instances where it is likely to yield substantial quality improvements.

This makes a simple claim such as 'ATOF uses an intelligent router' insufficiently differentiated. The relevant research question is narrower:

> Can an online controller allocate a finite search budget among complementary partitioning neighborhoods or solver components using observed marginal return, while preserving solution quality?

## Experimental controller now implemented

ATOF now exposes a research-only `hybrid_policy="marginal"` mode on `BLOCReloc.refine()`.

The controller follows an auditable sequence:

1. use the first eligible expensive pass as calibration;
2. record local and hybrid gain per structural-work unit;
3. after the cooldown/stagnation gate, pay for the hybrid operator only when its observed marginal return is at least as good as the local return;
4. adapt the next hybrid sample budget within a bounded 0.25x–2x range of the configured base budget.

This is deliberately **not a public/default routing policy**. It is an experimental mechanism for the quality-vs-compute study below. The controller is tested independently, while the external state-of-art benchmark remains the primary baseline gate.

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
- both are therefore reported in the same structural work unit rather than treating the number of random samples as equivalent computation;
- adaptive witness probes are also charged in the same structural work unit, so probe-based abstention cannot make the controller appear cheaper by omitting its measurement cost.

The trace records local work, hybrid work, probe work, total work, gain, and gain-per-work for each iteration. Wall-clock time remains a separate, machine-specific measure and is not replaced by this proxy.



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

## Equal-work frontier gate

The external controller artifact now persists a compact per-iteration structural-work curve for every graph×seed×policy. In addition to endpoint comparisons, the gate evaluates each controller against the fixed policy at the common per-graph, per-seed work budget: for each pair, it uses the best recorded edge cut reached at or before the smaller of the two final work totals, then aggregates seeds to the graph level.

This separates two questions that endpoint metrics can conflate:

- did the controller spend less or more total work?
- at the same available work, did it reach a lower edge cut?

The equal-work comparison is the primary evidence path for any future claim that marginal allocation creates a quality advantage rather than simply buying more computation.

## Current evidence boundary

ATOF does not yet satisfy those conditions. The current credit-routing experiment was therefore kept out of main after observing individual quality regressions despite meaningful compute savings. The current state-of-art benchmark is intended to establish the stronger external baseline before revisiting dynamic allocation.

## Reference

Schrape et al., SEA 2026, 'Engineering Learned Heuristics to Improve Clustering for Multilevel Graph Partitioning': https://doi.org/10.4230/LIPIcs.SEA.2026.25