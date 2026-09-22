# Independent DIMACS transfer: frozen 26-graph result

This validation tests the locked ATOF router protocol on a prespecified independent corpus from the DIMACS 10th Implementation Challenge clustering testbed.

## Block architecture

The heavy benchmark is partitioned into 12 reusable blocks:

- development: 7 graphs
- external: 4 graphs
- SNAP routine: 6 graphs
- SNAP scalability: 3 single-graph blocks
- DIMACS: 6 single-graph blocks

Each block computes the nine candidate strategies once for k=2, seeds 42/101/2024, and 25 BLOC-RELOC refinement iterations. The block JSON is the reusable graph-local benchmark state.

The aggregation job consumes only those block JSON files. It does not rerun partitioning or topology profiling.

## Frozen protocol

- 26 total graphs across five held-out corpora.
- 9 candidate partitioning strategies, including independently validated METIS and KaHIP.
- Three locked router configurations:
  - all + IQR + L2
  - global paths + IQR + L2
  - global paths + min-max + L2
- True leave-one-corpus-out transfer.
- Majority control recomputed for each held-out corpus.
- No feature, scaling, metric, or router hyperparameter tuning.

Workflow run: 35672597211.

Aggregate artifact: atof-independent-dimacs-transfer.

Aggregate artifact SHA-256:

4c5f8221b125c4c40485715d60adfb1220ae6e4b061d793c771e175720d42507

The frozen oracle distribution across the 26 graphs is:

- KaHIP: 16
- Kernighan-Lin: 4
- METIS: 3
- BLOC-RELOC baseline: 1

## Frozen transfer metrics

| Configuration | Nearest regret | Centroid regret | Majority regret | Nearest agreement |
|---|---:|---:|---:|---:|
| all + IQR + L2 | 0.212004 | 0.455716 | 0.184661 | 0.616667 |
| global paths + IQR + L2 | 0.119020 | 0.611909 | 0.184661 | 0.621429 |
| global paths + min-max + L2 | 0.249684 | 0.566663 | 0.184661 | 0.521429 |

## Graph-level robustness

The secondary analysis compares each router's graph-level relative regret against the majority control.

For global_paths_iqr_l2 nearest:

- mean delta: +0.002784
- bootstrap 95% CI: [-0.191083, 0.169927]
- better graphs: 4
- worse graphs: 5
- ties: 17
- exact two-sided sign-test p: 1.0

For all_iqr_l2 nearest:

- mean delta: +0.031550
- bootstrap 95% CI: [-0.021782, 0.101441]
- better graphs: 2
- worse graphs: 3
- ties: 21
- exact two-sided sign-test p: 1.0

For global_paths_minmax_l2 nearest:

- mean delta: +0.081129
- bootstrap 95% CI: [-0.007375, 0.198366]
- better graphs: 2
- worse graphs: 6
- ties: 18
- exact two-sided sign-test p: 0.289063

Therefore, the lower fold-balanced macro regret of global_paths_iqr_l2 should not be treated as established graph-level superiority over the majority control on this 26-graph sample.

## Reuse rule

Future routing, statistical, sensitivity, and reporting analyses should consume the frozen block/aggregate state instead of rerunning the nine partitioning strategies.

The public/default router remains unchanged by this validation.
