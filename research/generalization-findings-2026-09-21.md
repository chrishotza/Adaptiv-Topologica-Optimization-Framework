# ATOF generalization findings — 2026-09-21

## Reproducible execution

The first live multi-corpus study completed successfully as GitHub Actions run **35564691090** on commit **fa3e35967f3d66e249215dc867d67dc2663d80a8**.

It evaluated 15 held-out graphs:

- 7 development graphs;
- 4 external reference graphs;
- 4 routine SNAP graphs.

The result artifact 'atof-generalization-results' had SHA-256:

~~~text
8af6a0417449e4b38c38e7fab4969b5101b934965c0fbeee18e574b16beea5a2
~~~

The stricter leave-one-corpus-out transfer study completed successfully as GitHub Actions run **35565310315** on commit **641bcb17fc9e564d057c39d971d952e7ebaf8cfd**.

Its result artifact 'atof-generalization-results' had SHA-256:

~~~text
801cabec2dbafd7635750659ba8bdd617423a4aa23ba5235fbcf955fdfed087b
~~~

Both the ordinary CI run and the generalization workflow were successful on commit 641bcb17fc9e564d057c39d971d952e7ebaf8cfd.

## Within-corpus held-out routing

The aligned 15-graph study produced:

| Corpus | Graphs | Learned agreement | Global agreement | Learned mean relative regret | Global mean relative regret |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 7 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| External | 4 | 0.5000 | 0.7500 | 0.4792 | 0.0417 |
| SNAP | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

The combined micro summary was 0.8667 learned oracle agreement versus 0.9333 for the fixed global control. The macro summary was 0.8333 versus 0.9167.

These aggregates are descriptive only.

## Oracle-distribution diagnostic

The routing target is not equally diverse across corpora.

### Development

All seven graph-level oracles were 'kernighan_lin'.

### External

Three of four graph-level oracles were 'kernighan_lin'; one was 'bloc_reloc_baseline'.

### SNAP

All four graph-level oracles were 'kernighan_lin'.

Therefore, 100% learned agreement on SNAP is not evidence by itself that topology-conditioned routing was learned. A fixed 'kernighan_lin' strategy receives the same 100% agreement on that corpus.

## True leave-one-corpus-out transfer

The stricter experiment trains the topology router only on graph-level oracle labels from the other two corpora and tests it on the entire held-out corpus.

| Test corpus | Graphs | Learned agreement | Majority-control agreement | Heuristic agreement | Learned mean relative regret | Majority mean relative regret |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development | 7 | 0.1429 | 1.0000 | 0.0000 | 3.4738 | 0.0000 |
| External | 4 | 0.7500 | 0.7500 | 0.2500 | 0.0417 | 0.0417 |
| SNAP | 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

The macro transfer summary was:

- learned oracle agreement: **0.6310**
- majority-control agreement: **0.9167**
- heuristic agreement: **0.0833**
- learned mean relative regret: **1.1718**
- majority-control mean relative regret: **0.0139**
- heuristic mean relative regret: **2.8215**
- learned minus majority mean relative regret: **+1.1579**

## Interpretation

The current evidence does **not** support treating the nearest-centroid topology router as a robust cross-corpus transfer policy.

The clearest negative signal is the held-out development corpus: the learned router matched only 1 of 7 graph-level oracles while the majority-control matched all 7.

The external corpus shows parity between the learned router and the majority-control on this small four-graph sample.

The SNAP result is structurally non-diagnostic for adaptive routing because all four SNAP graph-level oracles were the same strategy, 'kernighan_lin'.

The transparent heuristic selector also does not currently provide a reliable routing policy on these corpora. Its agreement is low and its relative regret is substantially larger in the reported experiments.

## What this changes

The next research target is no longer “add more routing code.” It is to increase the amount and diversity of evidence before changing the model.

The strongest next experiments are:

1. expand the empirical corpus so that graph-level oracle labels are not dominated by one candidate strategy;
2. add additional strong, canonical partitioning baselines so the oracle has a genuinely heterogeneous strategy set;
3. keep leave-one-corpus-out evaluation as the primary transfer test;
4. compare the learned router against fixed and majority controls before introducing more complex meta-learning;
5. preserve per-corpus oracle distributions so aggregate agreement can never hide a degenerate target.

No universal generalization claim is made from these runs.


## Latest seven-strategy / dual-router evidence

GitHub Actions run **35570306006** completed successfully on commit **20a5ab86bff781733cdc2fcd792564739cad8397**.

The benchmark used one fixed k=2 candidate set across the three corpus tiers:

- round-robin balanced;
- random balanced;
- BLOC-RELOC baseline;
- BLOC-RELOC affinity;
- spectral bisection;
- balanced spectral-modularity bisection;
- NetworkX Kernighan-Lin.

Artifact SHA-256:

~~~text
3f6fa73086da7b67f95c4164a2a94b341fdd33e1f20afcf326267474a6df978f
~~~

Oracle distribution:

| Corpus | Graphs | Oracle distribution |
| --- | ---: | --- |
| Development | 7 | Kernighan-Lin: 5; spectral bisection: 2 |
| External | 4 | BLOC-RELOC baseline: 1; Kernighan-Lin: 2; spectral bisection: 1 |
| SNAP | 4 | Kernighan-Lin: 4 |

True leave-one-corpus-out macro transfer:

| Router/control | Agreement | Mean relative regret |
| --- | ---: | ---: |
| Centroid | 0.4167 | 1.2280 |
| 1-NN | 0.4405 | 0.8171 |
| Majority | 0.7381 | 0.3242 |
| Heuristic | 0.0833 | 6.2860 |

The 1-NN router therefore reduces transfer regret versus the centroid router, but remains behind the majority control. SNAP remains non-diagnostic for adaptive routing because all four SNAP graph-level oracles are Kernighan-Lin.

This is descriptive evidence on the current corpus, not a universal generalization result.

## Topology feature ablation — run 3

GitHub Actions workflow **35573176515** completed successfully on commit **f03079bdba77ccb9b0da46ea1117f62cbe5d1ddc**. Artifact SHA-256:

~~~text
010e223092ee07df23b93eb79ee728feeb8a4f3697f9c3787ee2baefa0dc0f03
~~~

The study used the same 15-graph, leave-one-corpus-out protocol and compared centroid, 1-NN, majority, and heuristic routing under seven feature configurations.

| Feature set | Centroid regret | 1-NN regret | Majority regret | 1-NN agreement |
| --- | ---: | ---: | ---: | ---: |
| All features | 1.2280 | 0.8171 | 0.3242 | 0.4405 |
| Without degree/hub | 0.7042 | 0.7387 | 0.3242 | 0.4762 |
| Without mesoscopic | 1.1966 | 0.5845 | 0.3242 | 0.4048 |
| Without global paths | 5.3150 | 0.5684 | 0.3242 | 0.4881 |
| Without degree/hub + mesoscopic | 0.7713 | **0.5565** | 0.3242 | 0.4405 |
| Without degree/hub + global paths | 5.1911 | 0.6504 | 0.3242 | **0.5238** |
| Without mesoscopic + global paths | 5.3235 | 0.5845 | 0.3242 | 0.4048 |

Interpretation: for the current corpus, the 1-NN router is most competitive when the feature space is reduced to the global-path family (the complement of degree/hub and mesoscopic groups), reaching 0.5565 mean relative regret. Removing global-path features is especially damaging to the centroid router, while 1-NN is much more stable under that ablation.

These results are an evidence-guiding ablation, not evidence that any feature family is universally causal or optimal. The majority control remains lower-regret than every topology-conditioned configuration in this corpus.

The practical implication is to test a **global-path-only 1-NN transfer candidate** on a larger and more heterogeneous empirical corpus before changing the public default router.


## Routine SNAP corpus expansion

The routine empirical tier was expanded from four to six graphs by adding **CollegeMsg** and **reachability**. CollegeMsg is a temporal messaging network from UC Irvine; reachability is an asymmetric airline-travel reachability network. The benchmark uses their edge endpoints as static connectivity and does not use temporal, weight, or metadata semantics.

## Expanded six-SNAP transfer result

Run **35574236663** completed successfully on commit **f603429a0c485b8c6c9692bca7c223f75cfce64e** with artifact SHA-256 **4a2cc793189902ecd5e217f6ffd6b880d9d0c9ad8039f674ce13284da9a2e6b8**.

The expanded routine corpus has six SNAP graphs and 17 graphs total. Macro transfer relative regret was **2.6916** for centroid, **0.7744** for 1-NN, **0.3242** for majority, and **6.2147** for the heuristic. Macro oracle agreement was **0.4444**, **0.4603**, **0.7381**, and **0.0833**, respectively.

The added SNAP graphs do not diversify the SNAP oracle itself: all six SNAP graph-level oracles remain Kernighan-Lin. Their value is therefore primarily in stressing topology-space transfer rather than creating a heterogeneous SNAP oracle target.


## Current 17-graph scaling ablation and confirmatory phase

The routine SNAP tier was expanded to six graphs, bringing the empirical corpus to 17 graphs total. The expanded true leave-one-corpus-out transfer result (workflow **35574236663**) reports macro mean relative regret of **2.6916** for centroid, **0.7744** for 1-NN, **0.3242** for majority, and **6.2147** for the heuristic; macro oracle agreement is **0.4444**, **0.4603**, **0.7381**, and **0.0833**, respectively.

A subsequent router-scaling ablation froze the 17-graph protocol while varying feature subsets, scaling modes, and distance metrics. The best observed centroid configuration was **global-path features + IQR scaling + L2**, with **0.4893** mean relative regret. The strongest observed 1-NN configurations in the tested family were **global-path + min-max/std + L2**, with **0.5757** mean relative regret. The majority control remained at **0.3242**.

These values are exploratory candidates only. They are being evaluated by a locked three-way confirmatory workflow:

1. all features + IQR + L2;
2. global-path features + IQR + L2;
3. global-path features + min-max + L2.

In parallel, the oracle-stability workflow quantifies seed consensus, oracle margins, and oracle-strategy concentration across the same corpus. No public routing default is changed by the scaling ablation alone.


## Oracle stability result

GitHub Actions run **35580179658** completed successfully on commit **5c236f2b855b842519c5bc90d9ec5aac505362ea**.

The 17-graph oracle-stability study found:

| Corpus | Graphs | Unique oracles | Mean seed consensus | Mean relative margin | Median relative margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 7 | 2 | 1.0000 | 0.2331 | 0.2692 |
| External | 4 | 3 | 0.8333 | 0.0260 | 0.0000 |
| SNAP | 6 | 1 | 1.0000 | 0.4991 | 0.4611 |

Development and SNAP are fully seed-stable. External is less separated: its median oracle margin is zero because several candidate strategies tie or nearly tie on the small reference graphs. The oracle target is therefore usable, but external cases should be treated as lower-confidence labels.

## Locked confirmatory result

GitHub Actions run **35580437557** completed successfully on commit **0b0c57fc556c08cad840970438cf92dec54b354f**.

| Configuration | Centroid regret | 1-NN regret | Majority regret |
| --- | ---: | ---: | ---: |
| all + IQR + L2 | 0.6408 | 0.6002 | 0.3242 |
| global paths + IQR + L2 | **0.4673** | 0.6232 | 0.3242 |
| global paths + minmax + L2 | 0.5649 | **0.5843** | 0.3242 |

The locked confirmatory run confirms that feature representation and scaling materially affect topology-router transfer, but the majority control remains lower-regret than every learned configuration tested here.

### Decision after the confirmatory phase

The appropriate next step is **not another topology-feature sweep**. The current evidence supports three statements:

1. the graph-level oracle is generally stable across seeds;
2. routing performance is sensitive to representation/scaling choices;
3. the current seven-strategy oracle is too concentrated—especially on SNAP—for adaptive routing to be a convincing improvement over a fixed majority strategy.

The next research increment should therefore enlarge or diversify the **candidate strategy space** with additional strong, objective-aligned partitioning baselines, then rerun the same locked leave-one-corpus-out protocol. The majority control and per-corpus oracle distribution should remain mandatory controls.

No public default-router change is justified by the current confirmatory evidence.
