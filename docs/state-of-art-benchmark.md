# State-of-art benchmark protocol

ATOF now has a dedicated head-to-head benchmark for the current balanced graph-partitioning comparison surface.

## Why this exists

The repository already had separate validation experiments for BLOC-RELOC, METIS, KaHIP, router transfer, and adaptive refinement. Those studies answer different questions. This protocol puts the main candidates under one auditable contract so that quality, exact balance, and runtime can be read together on the same 20-graph corpus.

The benchmark is deliberately not a claim that ATOF is already state of the art. It is the measurement gate required before making such a claim.

## Locked corpus

The protocol uses the expanded corpus already validated by the repository:

- seven synthetic development families;
- four external NetworkX reference graphs;
- six routine SNAP graphs;
- three SNAP scalability graphs.

That gives 20 graph-level test instances. SNAP source direction/sign semantics are normalized to ATOF's current unweighted undirected objective; the source metadata and provenance remain in the manifest.

## Locked objective

The current state-of-art benchmark is intentionally locked to:

- k=2;
- unweighted edge cut;
- floor/ceil balanced blocks;
- seeds 42, 101, 2024;
- 25 local refinement iterations.

k=2 is a comparability contract, not a statement that k-way partitioning is unimportant.

## Candidate surface

The first locked comparison contains:

1. BLOC-RELOC baseline;
2. BLOC-RELOC affinity;
3. BLOC-RELOC + fixed hybrid refinement;
4. BLOC-RELOC + state-aware adaptive refinement;
5. NetworkX Kernighan-Lin;
6. METIS;
7. KaHIP;
8. KaMinPar default;
9. KaMinPar strong.

The hybrid settings are fixed at period 5 and 100 sampled two-swaps. The adaptive controller uses 20 boundary-aware witness samples and a witness patience of 2.

The benchmark records every graph/seed/strategy row, including failures, rather than silently dropping unavailable candidates.

## What is compared

For each graph and strategy the manifest records:

- edge cut;
- balance error;
- runtime;
- hybrid pass/probe metadata where applicable;
- graph provenance;
- software/runtime metadata.

The graph-level summary then reports:

- the best observed mean edge cut;
- each strategy's relative quality gap to that graph best;
- runtime normalized to the graph's median strategy runtime.

This makes the analysis resistant to a single global runtime scale dominating across graph sizes.

## Statistical discipline

The primary unit remains the graph, not the individual random seed. Seeds are repeated measurements inside each graph and are averaged before cross-graph summaries.

No router is trained on this benchmark. It is a direct solver comparison.

No default/public selection policy is changed by the result.

## Current state-of-art references

KaMinPar is a current shared-memory/distributed multilevel partitioner with Python bindings and explicit large-k/scalability support. The project documents default, eco, strong, and large-k configurations. The Python package is available on Linux/macOS; version 3.7.3 was released in March 2026.

- https://github.com/KaHIP/KaMinPar
- https://pypi.org/project/kaminpar/

A 2025 paper, Linear-Time Multilevel Graph Partitioning via Edge Sparsification, reports a linear-time multilevel design integrated into KaMinPar, with an average 1.49x speedup and up to 4x on some instances at approximately 1% solution-quality loss in its evaluation.

- https://arxiv.org/abs/2504.17615

METIS remains a canonical multilevel recursive-bisection/k-way reference implementation.

- https://github.com/KarypisLab/METIS

KaHIP remains a high-quality multilevel family with sequential, shared-memory, distributed, evolutionary, and ILP-assisted variants.

- https://github.com/KaHIP/KaHIP

Learned graph-partitioning approaches are also part of the research surface. PR-GPT, for example, combines pretraining on smaller graphs, inductive inference, and refinement to target faster large-graph partitioning.

- https://arxiv.org/abs/2409.00670

## Next gates

Gate A — current PR: establish a single reproducible 20-graph comparison for k=2.

Gate B: add a verified KaMinPar adapter and run it under the same graph-level accounting. The adapter must preserve provenance and must not fabricate seed comparability if the binding does not expose a seed control.

Gate C: run a matched k-way study (at minimum k=4) over the subset of candidates that support the same contract.

Gate D: evaluate the research question that is specific to ATOF: whether dynamic allocation of local versus hybrid refinement work can move the Pareto frontier of quality versus compute, rather than merely changing which static solver wins.

Only after those gates are green should a stronger state-of-art claim be considered.