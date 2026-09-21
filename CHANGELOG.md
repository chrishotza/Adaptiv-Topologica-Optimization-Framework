# Changelog

## 0.3.0 — 2026-09-21

### Added

- Graph-aware paired bootstrap statistics over canonical benchmark graphs.
- Deterministic 95% bootstrap intervals for graph-level mean differences.
- Paired win/tie counts and a standardized paired effect summary.
- Statistical benchmark runner under experiments/run_statistical_analysis.py.
- Benchmark provenance now records the executing Git commit SHA when available.
- Regression coverage for the optional BLOC-RELOC hybrid two-swap path.

### Methodology

- Repeated seeds are aggregated within graph before uncertainty analysis.
- Bootstrap resampling occurs over graphs rather than seed rows.
- Statistical intervals are explicitly limited to uncertainty within the seven-graph synthetic development suite.
- No multiplicity correction is claimed in the initial statistical layer.

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
