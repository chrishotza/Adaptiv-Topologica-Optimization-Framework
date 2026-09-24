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

The adaptive-selection sequence is intentionally cumulative.

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
| #106 | Does the online selector survive a larger fixed seed grid? | Completed five-seed replication. On the fixed 20-graph corpus and 11-strategy selector protocol, top-1 mean regret was 10.16% and selector regret 1.95%, a paired delta of -8.21 percentage points. The graph-level bootstrap 95% CI was [-23.62, 0] pp, so this replication strengthened consistency but did not establish definitive statistical separation from zero. |
| #108 | Does topology routing transfer from bisection to a genuine k=4 partitioning setting? | Completed frozen k=4 leave-one-corpus-out study on 20 graphs × 3 seeds × 8 strategies. On the final corrected HEAD, centroid routing had 0.714% mean relative regret and nearest routing 0.445%, versus 3.408% for the majority control. Paired bootstrap 95% CIs for router-minus-majority were [-6.356, -0.013] pp and [-6.617, -0.202] pp respectively. This is domain-local transfer evidence within graph partitioning, not cross-domain generality. |

The sequence matters: later experiments are attempts to explain or stress-test earlier effects, not a stack of independently selected wins.

## Current strongest research question

The strongest current research question is not: Can ATOF always choose the best graph partitioner?

The better-posed question is: Under a fixed graph-partitioning contract, can topology-only information plus training-fold outcomes support a bounded, oracle-free decision about when to spend an additional solver action?

A second research question is now established as a separate line: whether topology-based routing transfers across partitioning cardinality within the same graph domain, from k=2 to genuine k-way k=4 partitioning.

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
- validity of the adaptive-selection research outside graph partitioning;
- cross-domain generality merely from the k=4 result.

The k=4 experiment addresses a narrower and falsifiable question: transfer across partitioning cardinality while holding the graph domain fixed.

A future cross-domain validation should be treated as a new research program with its own benchmark, oracle definition, costs, and held-out protocol rather than inferred from graph results.

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

The final k=4 evidence currently corresponds to the corrected branch HEAD and successful workflow artifact produced from commit 72ba33ae2610a362eefa471def06d485244cc02d.

## Promotion rule

No research experiment automatically changes the public/default ATOF behavior.

A research finding becomes a product candidate only after:

- semantic correctness is established;
- the frozen protocol passes;
- fresh held-out evaluation succeeds;
- uncertainty is reported;
- the result is replicated or independently stress-tested;
- the product contract is updated explicitly.

The k=4 routing experiment made no production/default change.

## Research directory map

- experiments/ — executable benchmark protocols.
- research/ — frozen findings and historical summaries.
- .github/workflows/ — CI and benchmark gates.
- docs/claims.md — external claim boundary.
- AGENTS.md — machine-facing operating rules.
- llms.txt — compact AI-oriented repository index.
