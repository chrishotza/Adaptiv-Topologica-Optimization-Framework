# Legacy research findings

This document records selected findings inherited from the predecessor repositories.

## ATOF predecessor

The predecessor benchmark suite showed that performance varied by graph family. Its stored family table had BLOC-RELOC ahead on several synthetic structural families while another local-search baseline led on the SNAP Real family.

These are historical benchmark outputs, not a fresh benchmark of the cleaned public implementation.

## BLOC-RELOC v2 predecessor

The Dynamics Observatory processed a stored trajectory dataset containing:

- 36,000 trajectory rows;
- 120 graphs;
- 6 configurations:
  - baseline
  - affinity
  - periodic
  - reactive
  - affinity_periodic
  - affinity_reactive

Its archived final synthesis explicitly limited interpretation to those tested configurations and treated correlations as exploratory rather than causal.

## Why preserve them?

The goal is to keep the research lineage inspectable without implying that historical artifacts automatically validate the new implementation.

The next canonical benchmark should be generated from this public code and recorded with its exact commit, environment, dataset, seed set, and objective.
