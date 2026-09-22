# State-of-art benchmark — first complete 11-candidate result

## Scope

This report summarizes workflow run `State-of-art benchmark #40` on commit `340295b321dcbd42ad1126202afb8e35f71697eb`.

The run contains 660 valid rows: 20 graphs × 3 seeds × 11 candidate strategies.

Recorded environment:

- ATOF 0.6.0
- NetworkX 3.7
- PyMetis 2025.2.2
- KaHIP 3.25
- KaMinPar 3.7.3
- Mt-KaHyPar 1.6.2

## Validity

All 660 rows completed successfully. KaMinPar default and strong are now included after moving to the explicit `max_block_weights=[ceil(n/k)] * k` API, matching ATOF's floor/ceil balance contract.

The benchmark isolates every native backend in its own worker process. Graph loading/backend initialization are excluded from solver timing for KaMinPar and Mt-KaHyPar. The objective is recomputed consistently in Python.

## Aggregate quality and runtime

`relative_quality_gap` in the machine manifest is a fraction. The table below reports the same metric as a percentage.

| Strategy | Graphs | Mean relative quality gap | Median relative quality gap | Mean runtime / graph median |
|---|---:|---:|---:|---:|
| Mt-KaHyPar default | 20 | 10.79% | 0.00% | 0.896x |
| Mt-KaHyPar quality | 20 | 11.51% | 0.00% | 0.924x |
| KaMinPar default | 20 | 16.45% | 0.40% | 0.467x |
| KaMinPar strong | 20 | 16.45% | 0.40% | 0.506x |
| KaHIP | 20 | 17.98% | 0.00% | 11.979x |
| METIS | 20 | 19.16% | 5.39% | 0.168x |
| NetworkX Kernighan-Lin | 20 | 54.26% | 10.88% | 0.764x |
| BLOC-RELOC hybrid fixed | 20 | 282.24% | 84.45% | 1.615x |
| BLOC-RELOC adaptive | 20 | 282.37% | 83.94% | 1.624x |
| BLOC-RELOC baseline | 20 | 776.80% | 206.77% | 1.029x |
| BLOC-RELOC affinity | 20 | 783.49% | 220.19% | 1.154x |

These figures are graph-level averages over three seeds. They do not represent a universal ranking; they describe this locked 20-graph CPU experiment.

## Which methods reach the graph best

When ties are counted, the number of graphs on which each method attains the minimum mean edge cut is:

- Mt-KaHyPar default: 14/20
- Mt-KaHyPar quality: 12/20
- KaHIP: 11/20
- KaMinPar default: 10/20
- KaMinPar strong: 10/20
- METIS: 8/20
- NetworkX Kernighan-Lin: 6/20
- BLOC-RELOC baseline: 1/20
- BLOC-RELOC hybrid fixed: 1/20
- BLOC-RELOC adaptive: 1/20

These counts overlap because 13 of the 20 graphs contain ties among multiple candidates.

## The main ATOF finding

Fixed hybrid refinement is a real improvement over plain BLOC-RELOC on this corpus, but it is still far from the strongest multilevel baselines under the same objective.

Relative to Mt-KaHyPar default, the hybrid fixed strategy has a mean graph-level cut gap of about 265.82% and a median gap of about 59.94%; it is not better than Mt-KaHyPar on 19 of 20 graphs and ties it on one.

The safe adaptive controller is almost identical to fixed hybrid on this corpus: compared with fixed hybrid it is better on 2 graphs, tied on 15, and worse on 3, with mean runtime ratio about 1.013x. It therefore does not yet establish a dynamic-allocation advantage.

## KaMinPar result

KaMinPar default and strong both produced valid results on all 20 graphs. They were within 5.60% mean relative cut of Mt-KaHyPar default when compared graph-by-graph, tied with Mt-KaHyPar on many instances, and better on 3 of 20 graphs under this specific seed/corpus protocol. Their runtime ratios to graph median were substantially lower than Mt-KaHyPar in this single-threaded Python environment.

This is not a statement about the broader performance of the KaMinPar project: its production configurations and published scalability results are designed for parallel execution, and hardware/thread counts matter.

## Research conclusion at this stage

The benchmark has now established a strong external baseline boundary.

1. The multilevel family remains substantially ahead of the current ATOF BLOC-RELOC refinement family on this corpus.
2. The current hybrid refinement is valuable, but it is not yet competitive with mature multilevel methods in final cut quality.
3. Parameter tuning alone is unlikely to close the observed gap efficiently.
4. The next legitimate novelty target is therefore the quality-versus-compute frontier: whether an adaptive controller can choose when and where to spend additional search budget so that it approaches the quality of strong multilevel solvers at materially lower incremental compute.
5. That experiment must include the learned-coarsening SEA 2026 baseline, not only classical solvers.

## Next gates

- Execute the k=4/8/32/64 benchmark over the same 20 graphs.
- Reproduce the SEA 2026 learned-coarsening implementation from its archived Mt-KaHyPar 1.5.3 snapshot.
- Materialize a reproducible subset of the 118-graph SEA Set A and preserve graph-level train/test separation.
- Build the dynamic compute-allocation frontier experiment against the fixed external baselines.