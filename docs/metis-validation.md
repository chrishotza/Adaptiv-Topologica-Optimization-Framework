# METIS strategy validation

The current seven-strategy routing study has a concentrated oracle, especially in the SNAP corpus. The oracle-stability experiment showed that the labels are generally reproducible across seeds, so the next question is whether the candidate strategy space is itself too narrow.

This experiment adds METIS multilevel bisection as an independent partitioning family. PyMetis is a Python wrapper around METIS and exposes part_graph with target partition weights.

ATOF requires exact two-way balance. METIS is therefore run with a 50/50 target and any residual size imbalance is repaired deterministically by moving the vertices with the smallest immediate cut increase until the exact floor/ceil split is reached.

The experiment does not add METIS to the router. It answers a narrower question first:

> Does an independent, strong partitioning family diversify the graph-level oracle?

Run:

~~~bash
python -m experiments.run_metis_validation
~~~

The output is results/generalization/metis_validation.json.

The GitHub Actions workflow is METIS strategy validation.

## Interpretation

If METIS wins a meaningful subset of graphs, the next transfer study can use the expanded strategy set while preserving the majority control.

If METIS almost never wins and the oracle remains concentrated on Kernighan-Lin, adding METIS to routing is not justified; the next step should be a different strategy family or a broader graph corpus.

The repaired edge cut is the comparison metric. Raw METIS cut counts are retained only for provenance.

## Validation result

Run **35582563274** completed successfully with artifact **10631785520**. Across the 17-graph corpus, the expanded candidate oracle selected METIS on 8 graphs, Kernighan-Lin on 8, and BLOC-RELOC baseline on 1. The distribution by corpus is Development: METIS 6 / Kernighan-Lin 1; External: METIS 1 / Kernighan-Lin 2 / BLOC-RELOC 1; SNAP: METIS 1 / Kernighan-Lin 5.

This result justified the next experiment: the locked router transfer protocol was rerun with eight strategies, adding METIS as the sole new candidate. Run **35584123689** completed successfully with artifact **10632280359**.

The eight-strategy run reduced 1-NN graph-level relative regret by about 0.57–0.62 across all three locked configurations. A paired robustness analysis over the same 17 held-out graphs found exact one-sided sign-flip p-values of 0.002930, 0.003784, and 0.007568 for the three 1-NN comparisons. The centroid results moved in the same direction but were less consistent across configurations.

Detailed statistics and provenance are recorded in docs/metis-transfer-robustness.md and research/metis-transfer-statistical-robustness.json.

METIS therefore remains part of the **research candidate space**, but these results alone do not change the public/default router.
