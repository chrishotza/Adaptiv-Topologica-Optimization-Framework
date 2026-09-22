# SEA 2026 alignment protocol

ATOF's state-of-art work is explicitly aligned with the 2026 experimental surface used by Schrape et al. for learned coarsening inside Mt-KaHyPar.

## External benchmark dimensions

SEA 2026 evaluates Set A (118 graphs), Set B (69 graphs), Set I (38 large irregular graphs), and Set R (33 large regular graphs). The full Set A + Set I + Set R surface is 189 graph instances. The Zenodo record provides the benchmark data, training data, labels, and published results.

Source: https://zenodo.org/records/19387774

## Matched solver protocol

SEA evaluates k in {4, 8, 32, 64}, epsilon=0.03, five randomized runs per graph/k combination, and a one-hour time limit. Aggregate quality and runtime are arithmetic means over seeds and geometric means across instances.

ATOF now has a direct exact-software reference gate for the SEA 2026 Mt-KaHyPar artifact. It builds archived revision 6d12d9cf210390624f3757e9b5399469d2d2ae68 (software version 1.5.3), downloads the public Set A corpus with its published MD5, and executes the learned configuration against a controlled baseline configuration on a selectable subset of Set A.

The gate records the exact command, graph/seed/k identity, partition block counts, edge cut, runtime, and executable output tails. It preserves seed-level paired results and additionally aggregates each graph×k instance by arithmetic mean across seeds, then aggregates those instances by geometric mean. This mirrors the published aggregation hierarchy while keeping the raw runs auditable.

## Important training/test boundary

The SEA 2026 learned-coarsening method is trained using 20 graphs from Set B1-20, which are a subset of Set B. The exact-software reference gate is a measurement surface, not a training surface.

## Balance and objective semantics

The exact-software gate uses the published epsilon=0.03 contract rather than ATOF's product floor/ceil contract. Product parity and paper-protocol parity remain separate tracks.

## ATOF gaps against this protocol

1. Current direct ATOF benchmark: 20 graphs, k=2.
2. Current product external solver surface: METIS, KaHIP, KaMinPar, Mt-KaHyPar, NetworkX KL, BLOC-RELOC variants.
3. The exact SEA 2026 snapshot is now benchmarked on a selectable Set A subset through the learned-vs-baseline reference gate.
4. Matched k-way ATOF evaluation at k=4, 8, 32, 64 is independently gated.
5. Full 118-graph reproduction remains a manual scale gate.
6. Large Set I/R reproduction remains a separate scale tier.

## Execution gates

- Gate A: current 20-graph k=2 head-to-head.
- Gate B: matched product k-way study at k=4, 8, 32, 64.
- Gate C: exact SEA software reference on a controlled Set A subset.
- Gate D: full 118-graph Set A materialization and selected paper-protocol reproduction.
- Gate E: Set I/R scale tier.
- Gate F: dynamic compute-allocation evaluation against mature baselines.
