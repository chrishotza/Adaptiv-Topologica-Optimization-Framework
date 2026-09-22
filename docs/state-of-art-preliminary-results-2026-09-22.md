# Preliminary state-of-art benchmark results — 2026-09-22

## Scope

This report summarizes workflow run `State-of-art benchmark #32` on commit `f97ea9c90a5b0e76e7ea2a9586a57f944a5618d2`.

The run contains 660 rows: 20 graphs × 3 seeds × 11 candidate strategies.

Package versions recorded by the manifest:

- ATOF 0.6.0
- NetworkX 3.7
- PyMetis 2025.2.2
- KaHIP 3.25
- KaMinPar 3.7.3
- Mt-KaHyPar 1.6.2

## Important limitation

KaMinPar default and strong both exited with code `-11` in their isolated worker, across all 60 rows per strategy. Therefore KaMinPar is excluded from all quality aggregates below.

This is an integration failure, not a result about KaMinPar's partitioning quality. The benchmark treats those rows as unavailable rather than silently replacing them.

The adapter has since been changed to use KaMinPar's explicit `max_block_weights=[ceil(n/k)] * k` overload, matching ATOF's floor/ceil balance contract. A fresh execution is required before KaMinPar can enter the scientific comparison.

## Aggregate quality / runtime

Relative quality gap is the graph-level mean of `(strategy_mean_edge_cut - graph_best_edge_cut) / graph_best_edge_cut`. Runtime is normalized to each graph's median candidate runtime.

| Strategy | Graphs | Mean relative quality gap | Median relative quality gap | Mean runtime / graph median |
|---|---:|---:|---:|---:|
| Mt-KaHyPar default | 20 | 0.1079% | 0.0000% | 0.734x |
| Mt-KaHyPar quality | 20 | 0.1151% | 0.0000% | 0.749x |
| KaHIP | 20 | 0.1798% | 0.0000% | 10.243x |
| METIS | 20 | 0.1916% | 0.0539% | 0.154x |
| NetworkX Kernighan-Lin | 20 | 0.5426% | 0.1088% | 0.691x |
| BLOC-RELOC hybrid fixed | 20 | 2.8224% | 0.8445% | 1.343x |
| BLOC-RELOC adaptive | 20 | 2.8237% | 0.8394% | 1.365x |
| BLOC-RELOC baseline | 20 | 7.7680% | 2.0677% | 0.874x |
| BLOC-RELOC affinity | 20 | 7.8349% | 2.2019% | 0.980x |

These numbers are from one matched 20-graph, three-seed, 25-iteration CPU run. They are not a claim of universal superiority or state-of-the-art status.

## ATOF refinement signal

Compared with the plain BLOC-RELOC baseline, fixed hybrid refinement improved graph-level mean edge cut on 19 of 20 graphs and worsened none in this corpus, at a mean runtime ratio of about 1.64x relative to baseline. This confirms that the expensive local-search component materially closes part of the quality gap.

The safe adaptive controller was very close to the fixed hybrid endpoint on this corpus: relative to fixed hybrid, it was better on 2 graphs, tied on 15, and worse on 3, with mean edge-cut delta +6.68 raw cut units and a mean runtime ratio of about 1.013x. This reinforces the current decision not to promote a more aggressive dynamic policy without stronger evidence.

## External solver structure

Mt-KaHyPar default had the smallest mean relative quality gap among the available candidates. It achieved the best or tied-best mean edge cut on 14 of 20 graphs; Mt-KaHyPar quality did so on 12, KaHIP on 11, and METIS on 8 when ties are counted. These tie counts overlap because several graphs have identical best cuts across multiple solvers.

The distribution is heterogeneous. On several synthetic/reference graphs, multiple multilevel solvers tie at the same cut. On routine SNAP graphs, the relative ordering changes substantially across instances. On the three scalability graphs, Mt-KaHyPar default had the best mean cut on ca-GrQc and ca-HepTh, while Wiki-Vote was a difficult case for several methods under the current protocol.

## Research interpretation

The first external comparison changes the research question in a useful way.

1. BLOC-RELOC plus hybrid refinement is a meaningful quality improvement over plain BLOC-RELOC.
2. The current ATOF refinement family is still materially behind mature multilevel solvers on this 20-graph corpus.
3. The strongest immediate research target is therefore not another small BLOC parameter tweak.
4. The differentiating question remains whether ATOF can allocate compute dynamically and recover a better quality-vs-compute frontier than fixed refinement and mature multilevel baselines.

## Next validation

- rerun the corrected KaMinPar adapter using explicit max block weights;
- execute the k=4/8/32/64 benchmark with the same native-process isolation;
- reproduce the SEA 2026 learned-coarsening baseline from the archived Mt-KaHyPar 1.5.3 snapshot;
- expand from 20 graphs to the public SEA Set A while preserving graph-level holdouts;
- only then test dynamic compute allocation against the strongest external and learned baselines.

## Provenance

SEA 2026 reference: https://doi.org/10.4230/LIPIcs.SEA.2026.25
KaMinPar 3.7.3: https://github.com/KaHIP/KaMinPar/releases/tag/v3.7.3
Mt-KaHyPar: https://github.com/kahypar/mt-kahypar