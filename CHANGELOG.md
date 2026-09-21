# Changelog

## 0.2.0 — 2026-09-21

### Added

- Canonical topology benchmark with seven deterministic synthetic graph families.
- BLOC-RELOC baseline and degree-affinity variants.
- NetworkX Kernighan-Lin benchmark baseline for two-way partitions.
- Per-iteration optimization dynamics and activity observatory.
- Descriptive persistence, extinction, regime-comparison, and exploratory correlation metrics.
- Graph-level learned topology router using nearest centroids.
- Leave-one-graph-out routing evaluation with oracle agreement and regret metrics.
- Public ATOF command-line interface with graph profiling.
- CI smoke tests for package import, canonical benchmark, observatory, routing benchmark, and output validation.

### Methodology

- Strategy routing is evaluated at graph level to avoid seed-level leakage.
- Historical benchmark findings remain explicitly separated from the cleaned public implementation.
- Oracle results are used only as post-hoc evaluation references.
