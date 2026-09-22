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
9. KaMinPar strong;
10. Mt-KaHyPar default;
11. Mt-KaHyPar quality.

The hybrid settings are fixed at period 5 and 100 sampled two-swaps. The adaptive controller uses 20 boundary-aware witness samples and a witness patience of 2.

The benchmark records every graph/seed/strategy row, including failures, rather than silently dropping unavailable candidates. A graph-level comparison is only marked matched when all candidates have the required seed count. KaMinPar's Python binding mutates the Graph object during compute_partition and restores it afterward, so each worker keeps one strategy isolated from all other native extensions.

For unit-weight graphs, Mt-KaHyPar is requested with epsilon=0. KaMinPar is requested with explicit maximum block weights equal to ceil(n/k), which directly enforces the same floor/ceil balance contract. The benchmark then recomputes balance from every returned partition under ATOF's contract.

Mt-KaHyPar is evaluated through its current Python binding with one CPU thread. Graph loading and backend initialization are outside the timed partition call. Native C/C++ backends are also isolated one strategy per worker process so extension runtimes cannot corrupt each other. The default and quality presets are separate candidates; they are current multilevel baselines, not the SEA 2026 learned-coarsening model.

## What is compared

For each graph and strategy the manifest records:

- edge cut;
- balance error;
- runtime;
- hybrid pass/probe metadata where applicable;
- graph provenance;
- software/runtime metadata.

A graph is considered matched only when every candidate has the complete seed set for that protocol. Partial candidate coverage remains visible in the raw manifest but is excluded from graph-level and cross-graph aggregate results. Native worker payload parsing also tolerates non-JSON diagnostic lines and consumes only the final JSON payload line.

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

Gate B: KaMinPar integration is implemented and covered by the k=2 benchmark contract.

Gate C: the matched k-way scaffold is implemented for k=4,8,32,64 across the 20-graph corpus, but it is not yet an executed result.

Gate D: integrate the current Mt-KaHyPar backend as a direct baseline; this is implemented for default and quality presets. The SEA 2026 learned-coarsening model is still a separate research target.

Gate E: evaluate whether dynamic allocation of local versus hybrid refinement work can move the Pareto frontier of quality versus compute, rather than merely changing which static solver wins.

Gate F: selectively reproduce the SEA 2026 Set A experiment and preserve strict graph-level training/test separation.

Only after those gates are green should a stronger state-of-art claim be considered.