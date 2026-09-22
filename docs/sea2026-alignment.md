# SEA 2026 alignment protocol

ATOF's state-of-art work is now explicitly aligned with the 2026 experimental surface used by Schrape et al. for learned coarsening inside Mt-KaHyPar.

## External benchmark dimensions

The SEA 2026 paper evaluates:

- Set A: 118 graphs, 29k–53M edges;
- Set B: 69 graphs, a subset of Set A;
- Set I: 38 large irregular graphs, 5.4M–1.8B edges;
- Set R: 33 large regular graphs, 12M–575M edges.

Set A combines SuiteSparse, Network Repository, Walshaw, a semiconductor placement benchmark, and synthetic graph families. The full Set A + Set I + Set R surface is 189 graph instances. The Zenodo record provides the benchmark data, training data, labels, and published results. The complete archived dataset is large, so ATOF must use selective, provenance-preserving materialization rather than copying the full archive into Git.

Source: https://zenodo.org/records/19387774

## Matched solver protocol

SEA evaluates k in {4, 8, 32, 64}, epsilon=0.03, five random seeds per graph/k combination, and a one-hour time limit. Aggregate quality and runtime are arithmetic means over seeds and geometric means across instances.

That is the next matched protocol for ATOF after the current k=2 gate.

## Important training/test boundary

The SEA 2026 learned-coarsening method is trained using 20 graphs from Set B1-20, which are a subset of the 69-graph Set B. The authors report that most of Set A is therefore outside the training data. Their generalization experiment uses 8-fold cross-validation over Set A.

The training data itself contains one million sampled edges with equal sampling contribution from each training graph, then a 70/15/15 train/validation/test split at the edge-sample level.

ATOF must not reproduce a weaker graph-level leakage pattern by training a router on benchmark graphs and then evaluating those same graphs. Its cross-corpus router protocol therefore remains separate from the direct solver benchmark.

## What SEA 2026 demonstrates

The paper reports that learned coarsening improves solution quality over its Mt-KaHyPar baseline by 0.3–1.4% depending on configuration, with a 14% running-time overhead for its optimized AVX2 implementation. On Set A, the reported geometric mean cut is 0.34% better than baseline Mt-KaHyPar for the unconstrained refinement configuration and 1.4% better for the constrained configuration.

Metis-K is reported at roughly 20% worse geometric-mean cut than the learned approach on Set A, while Metis-R is similarly around 20% worse and about twice as slow as Metis-K. The paper notes that several Metis-K outputs were slightly over the stated balance bound due to rounding and were still treated as balanced in its presentation.

These are published results from a different hardware/software stack and are not directly comparable to ATOF wall-clock timings. They define the reference level ATOF needs to reproduce under a matched experimental contract.

## ATOF gaps against this protocol

1. Current direct benchmark: 20 graphs, k=2.
2. Current external solver surface: METIS, KaHIP, KaMinPar, NetworkX KL, BLOC-RELOC variants.
3. Missing high-quality learned-coarsening baseline: Mt-KaHyPar SEA 2026.
4. Missing matched k-way evaluation: k=4, 8, 32, 64.
5. Missing 118-graph Set A reproduction.
6. Missing large irregular/regular scale tier comparable to Set I and Set R.

## Research consequence

The strongest ATOF research question is now narrower and more demanding:

Can dynamic allocation of refinement/search budget produce a measurable quality-vs-compute improvement that survives comparison against mature multilevel partitioners and learned coarsening on unseen graph families?

That question is materially different from simply routing among BLOC-RELOC variants. It has to be evaluated against internal ML heuristics, not only external solver selection.

## Execution gates

- Gate A: current 20-graph k=2 head-to-head with KaMinPar.
- Gate B: matched k-way ATOF/METIS/KaHIP/KaMinPar study at k=4, 8, 32, 64.
- Gate C: add Mt-KaHyPar or the published SEA 2026 implementation as a direct baseline.
- Gate D: selectively materialize the 118-graph Set A benchmark and reproduce a subset of the published comparisons.
- Gate E: expand to Set I/R for scale-sensitive validation.
- Gate F: only then evaluate ATOF's dynamic compute-allocation controller against the mature baselines.

## References

- Schrape, Maas, Langedal, Seemaier, SEA 2026: https://doi.org/10.4230/LIPIcs.SEA.2026.25
- Supplementary dataset: https://doi.org/10.5281/zenodo.19387774
- Mt-KaHyPar SEA 2026 artifact: https://doi.org/10.4230/artifacts.26212