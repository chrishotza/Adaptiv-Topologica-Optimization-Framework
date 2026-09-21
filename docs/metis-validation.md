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