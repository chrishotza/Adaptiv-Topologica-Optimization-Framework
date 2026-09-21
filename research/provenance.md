# Research provenance

ATOF consolidates three predecessor repositories:

- `adaptive-topological-optimization`
- `bloc-reloc-v2`
- `cov-ia`

The public graph-optimization core is derived primarily from the first two because they belong to the same research line.

## Promoted

- topology profiling patterns from ATOF;
- the BLOC-RELOC refinement engine and dynamics-analysis concepts from BLOC-RELOC v2;
- explicit separation between implementation, measurement, evidence, and interpretation.

## Kept separate

COV-IA remains a separate prototype. Its predecessor used synthetic latency, accuracy, cost, and load models, so those values should not be presented as measurements from real inference hardware or production model serving.

## Curation rule

A component enters ATOF when it is reusable, internally coherent, testable, and aligned with topology-aware graph optimization. Historical repair scripts, duplicated versions, and ambiguous baselines stay outside the canonical implementation.
