# ATOF Open State-of-the-Art Lab

This repository treats the state of the art as a **living open test surface**, not a static bibliography.

## Coverage model

ATOF currently exposes a common product contract across:

- BLOC-RELOC;
- NetworkX Kernighan-Lin;
- METIS;
- KaHIP;
- KaMinPar;
- Mt-KaHyPar.

Research tracks extend this surface toward:

- k={4,8,32,64};
- SEA 2026 learned coarsening;
- large-scale Set A / Set I / Set R materialization;
- dynamic quality-vs-compute allocation;
- future multi-constraint and hypergraph objectives.

## Reproducible gates

### k=2

The locked comparison uses:

- 20 graphs;
- seeds 42, 101, 2024;
- 11 candidate strategies;
- balanced unweighted edge cut.

The resulting artifact is machine-readable and must be interpreted as a corpus-specific comparison.

### k-way

The matched research scaffold evaluates:

- k=4;
- k=8;
- k=32;
- k=64;

using the same corpus and seed set. Results are accepted only when every participating backend satisfies the exact floor/ceil balance contract.

### SEA 2026

The repository tracks the exact 2026 learned-coarsening software snapshot separately from current Mt-KaHyPar release presets. The Set A workflow downloads the public 118-graph corpus, verifies its published archive hash, records file-level provenance, and can run a controlled gate without vendoring the dataset.

The controlled Set A gate is intentionally not presented as an exact numerical reproduction of the paper's hardware/time protocol.

## How to add a frontier

When a new partitioning method appears:

1. identify its graph model, objective, constraints, and hardware regime;
2. determine whether those semantics match ATOF's current contract;
3. add it to the research map with a primary source and reproducible software reference;
4. implement an isolated benchmark adapter;
5. validate outputs against the common contract;
6. run a matched benchmark;
7. convert the useful portion into a product capability when the evidence is sufficient.

Methods that solve a different optimization problem should remain documented as adjacent frontiers rather than being forced into a misleading leaderboard.

## Quality-vs-compute track

The dynamic controller records gain and structural work for local and hybrid neighborhoods. Adaptive witness probes are charged in the same structural work unit as the search they inform.

The external dynamic-compute gate now evaluates fixed, adaptive, marginal, and no-hybrid controls on the locked 20-graph corpus with three seeds. It reports paired graph-level quality and work comparisons; this is the evidence gate for any future quality-vs-compute claim.

The current experimental policy:

- calibrates an expensive neighborhood;
- compares observed gain per work;
- decides whether another expensive pass is justified;
- adapts the next sample budget within bounded limits.

This is research infrastructure, not a default product claim.

## Evidence rule

Every result should answer four questions:

1. What exactly was measured?
2. On which graphs?
3. Under which objective, balance, seed, and hardware protocol?
4. Can another contributor reproduce it?

The answer to those questions is part of the contribution.
