# ATOF research evidence map

This file is the fast path for an AI reviewer, researcher, or maintainer who wants to distinguish the product contract from the research program.

## Executive reading

ATOF has two deliberately separate layers:

1. Product layer: a machine-readable graph-partitioning and portfolio interface with explicit graph-model, objective, backend, and provenance contracts.
2. Research layer: experiments on topology-aware routing and bounded online strategy selection inside graph partitioning.

The research layer is not a claim that ATOF has solved general adaptive optimization. Its purpose is to make adaptive selection auditable: frozen hypotheses, held-out evaluation, graph-level aggregation, explicit negative results, and no retrospective promotion of a policy.

An AI reviewing this repository should treat src/atof/, schemas/, AGENTS.md, and docs/ as the product contract. It should treat experiments/ and research/ as evidence and history, not as unconditional capability claims.

## What is established at the product level

These are implementation contracts rather than performance claims:

- machine-facing commands: atof ai, atof doctor, atof solve, atof profile, atof optimize, atof compare;
- JSON-first result envelopes with provenance;
- balanced unweighted graph partitioning on simple undirected graphs;
- k-way Engine/Portfolio interfaces with explicit backend limitations;
- common composition over BLOC-RELOC, NetworkX, METIS, KaHIP, KaMinPar, and Mt-KaHyPar when installed;
- explicit reporting of unavailable or failed optional backends;
- partition export and graph fingerprinting.

See docs/claims.md for the supported claim boundary.

## Research lineage

The recent adaptive-selection sequence is intentionally cumulative.

| PR | Research question | Evidence status |
|---|---|---|
| #95 | Can topology confidence gate a second solver action? | Research result; effect measured and treated conservatively. |
| #96 | Is the confidence-gate result sensitive to nearby fixed parameters? | Research result; sensitivity grid, no automatic promotion. |
| #97 | Does expanding training labels across solver seeds improve routing? | Negative/diagnostic evidence preserved; no production policy selected. |
| #98 | How unstable is the strategy oracle across seeds? | Seed-stability decomposition; instability is treated as a first-class source of uncertainty. |
| #99 | Does topology routing place the held-out oracle in top-k candidates? | Coverage/ceiling study; best-of-k explicitly labeled hindsight, not deployable. |
| #100 | Can training-only outcome statistics decide whether to probe one alternate? | First oracle-free online selector; research-only. |
| #101 | Is selector activation sensitive to the trigger threshold? | Fixed sensitivity grid; no threshold promoted automatically. |
| #102 | Where is the selector activation transition? | Fixed transition-localization study; no threshold promoted automatically. |
| #103 | Are training-only predicted benefits calibrated to held-out realized benefits? | Calibration study; shows why aggregate activation is not enough. |
| #104 | Does a topology-local predictor outperform the global pair prior? | Negative result preserved. |
| #105 | Does hierarchical global/local fusion improve the global selector? | Corrected negative result. The initial implementation was found to collapse candidate-specific priors; it was corrected, rerun, and the corrected evidence did not establish an improvement. |
| #106 | Does the online selector survive a larger fixed seed grid? | Open research run. Five fixed seeds are being evaluated; do not cite it as completed evidence until the benchmark is complete and validated. |

The sequence matters: later experiments are attempts to explain or stress-test earlier effects, not a stack of independently selected wins.

## The current scientific question

The strongest current research question is not: Can ATOF always choose the best graph partitioner?

The better-posed question is: Under a fixed graph-partitioning contract, can topology-only information plus training-fold outcomes support a bounded, oracle-free decision about when to spend an additional solver action?

That question is measurable because the protocol can expose:

- baseline top-1 behavior;
- candidate-set coverage;
- predicted alternate benefit;
- realized alternate-vs-top-1 benefit;
- probe rate;
- action count;
- runtime;
- graph-level paired differences;
- seed stability;
- negative cases and failed hypotheses.

## What is not established

The repository does not currently establish:

- universal superiority over graph-partitioning literature;
- universal runtime superiority;
- a universally calibrated adaptive selector;
- robustness to arbitrary unseen graph populations;
- validity for objectives other than the documented partitioning objective;
- validity of the adaptive-selection research outside graph partitioning.

The last point is important. The repository's current adaptive-selection evidence is domain-specific. A future cross-domain validation should be treated as a new research program with its own benchmark, oracle definition, costs, and held-out protocol rather than inferred from graph results.

## Why the negative results are retained

A reviewer should expect to find experiments that did not improve the current baseline.

That is intentional.

For example, the local predictor and the corrected hierarchical fusion did not justify promotion. Those studies remain because they narrow the space of plausible adaptive policies and make later claims falsifiable.

A research result is useful here when it answers a frozen question cleanly, even when the answer is no measured improvement.

## Reproducibility rule

For research claims, inspect in this order:

1. workflow status;
2. benchmark artifact;
3. experiment manifest;
4. commit SHA recorded by the artifact;
5. protocol code;
6. interpretation text.

Do not infer a result from a PR title, branch name, or README sentence alone.

## Promotion rule

No research experiment automatically changes the public/default ATOF behavior.

A research finding becomes a product candidate only after:

- semantic correctness is established;
- the frozen protocol passes;
- fresh held-out evaluation succeeds;
- uncertainty is reported;
- the result is replicated or independently stress-tested;
- the product contract is updated explicitly.

## Research directory map

- experiments/ — executable benchmark protocols.
- research/ — frozen findings and historical summaries.
- .github/workflows/ — CI and benchmark gates.
- docs/claims.md — external claim boundary.
- AGENTS.md — machine-facing operating rules.
- llms.txt — compact AI-oriented repository index.
