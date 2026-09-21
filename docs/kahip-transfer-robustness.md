# KaHIP 8→9 transfer robustness

The valid KaHIP validation was followed by a locked nine-strategy transfer experiment. This analysis pairs the 17 identical held-out graphs from the eight-strategy METIS run with the nine-strategy KaHIP run.

## Frozen protocol

The comparison keeps:

- 17 graphs: 7 development, 4 external, 6 SNAP;
- true leave-one-corpus-out transfer;
- k=2;
- seeds 42, 101, 2024;
- 25 BLOC-RELOC refinement iterations;
- the same three locked router configurations;
- majority and heuristic controls.

The only candidate-space change is the addition of kahip_kaffpa_strong_balanced to the existing eight-strategy set.

## Oracle transition

Adding KaHIP changes the graph-level oracle on 13 of 17 graphs.

| Oracle set | Distribution |
| --- | --- |
| Eight strategies | METIS 8; Kernighan-Lin 8; BLOC-RELOC baseline 1 |
| Nine strategies | KaHIP 13; Kernighan-Lin 3; BLOC-RELOC baseline 1 |

KaHIP is the strict minimum on 7 graphs, tied for the minimum on 6, and loses on 4.

This is strong evidence of oracle-space redefinition, but it is not by itself evidence that topology routing improved.

## Paired transfer effect

Endpoint delta is defined as:

nine-strategy relative regret minus eight-strategy relative regret.

Negative values indicate lower regret after adding KaHIP.

| Configuration | Router | Mean delta | Improved | Worsened | Exact sign-flip p | Bootstrap 95% CI |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| all + IQR + L2 | 1-NN | -0.0097 | 5 | 3 | 0.3555 | [-0.0538, 0.0363] |
| global paths + IQR + L2 | 1-NN | +0.0033 | 5 | 5 | 0.5508 | [-0.0457, 0.0518] |
| global paths + minmax + L2 | 1-NN | +0.0044 | 4 | 5 | 0.5723 | [-0.0444, 0.0527] |
| all + IQR + L2 | centroid | -0.2482 | 2 | 5 | 0.3281 | [-0.8559, 0.1321] |
| global paths + IQR + L2 | centroid | -0.2725 | 3 | 5 | 0.2500 | [-0.8750, 0.1079] |
| global paths + minmax + L2 | centroid | -0.2725 | 3 | 5 | 0.2500 | [-0.8750, 0.1079] |

The 1-NN paired intervals all include zero. The centroid mean delta is consistently negative, but its paired intervals also include zero.

The majority-control endpoint falls from 0.3787 to 0.0814 in all three configurations. This is a re-baselining effect because the majority training-corpus oracle changes when KaHIP enters the candidate set; it should not be interpreted as a fixed-policy treatment effect.

## Decision

The nine-strategy experiment establishes that KaHIP materially changes the oracle landscape on this corpus. It does not establish a statistically robust improvement of the topology-conditioned router itself.

Therefore:

1. do not change the public/default router;
2. do not perform another feature/scaler sweep on this evidence alone;
3. preserve the eight- versus nine-strategy paired results as the current robustness boundary;
4. prioritize corpus expansion and additional independent strategy diversity before making a routing-selection claim.

The exact paired statistics are frozen in research/kahip-transfer-robustness.json.
