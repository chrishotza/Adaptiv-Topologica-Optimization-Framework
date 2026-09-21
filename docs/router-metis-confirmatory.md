# METIS router confirmatory comparison

This experiment extends the locked router confirmatory protocol from seven to eight candidate strategies by adding the independently validated `metis_multilevel_balanced` family.

## Purpose

The preceding METIS validation showed that adding METIS materially diversifies the graph-level candidate oracle. This run asks the next empirical question: does that broader strategy space improve topology-conditioned transfer under the existing protocol?

## Locked protocol

- 17 graphs across development, external, and SNAP corpora.
- True leave-one-corpus-out transfer.
- Seeds: 42, 101, 2024.
- (k=2).
- 25 BLOC-RELOC refinement iterations.
- Candidate set: the existing seven strategies plus METIS.
- Three previously locked routing configurations:
  - `all_iqr_l2`
  - `global_paths_iqr_l2`
  - `global_paths_minmax_l2`
- Controls: centroid, 1-NN, majority, and heuristic.
- No new feature, scaler, metric, or router hyperparameter tuning is performed.

## METIS comparability

METIS is run with the independently validated two-way multilevel implementation and the same deterministic exact-balance repair used by `run_metis_validation.py`. The repaired edge cut is the value inserted into each graph's strategy means.

## Interpretation rule

This experiment is a direct comparison against the prior locked seven-strategy protocol. A lower relative regret remains better, and the majority control is retained as the fixed-frequency baseline. The result does not by itself justify changing the public/default router; any such change requires the resulting evidence to support it.

## Reproducibility

The workflow is `.github/workflows/router-metis-confirmatory.yml`. The output artifact is `atof-router-metis-confirmatory`, containing `results/generalization/router_metis_confirmatory.json`.

