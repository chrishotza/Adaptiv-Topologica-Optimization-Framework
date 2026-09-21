# Changelog

## Unreleased

### Added

- Cross-corpus routing aggregation utilities in atof.generalization.
- Separate micro and macro summaries so large corpora cannot silently dominate a combined routing report.
- Research protocol documentation for the next generalization milestone.
- Executable aligned study across development, external, and routine SNAP routing corpora.
- GitHub Actions workflow that runs the aligned study against live SNAP data and uploads provenance-bearing manifests.
- True leave-one-corpus-out transfer experiment with a majority-oracle control.

### Methodology

- Cross-corpus summaries preserve held-out graphs as the unit of routing analysis.
- The aggregation layer is descriptive infrastructure and does not claim universal generalization.

## 0.5.0 — 2026-09-21

### Added

- Reproducible SNAP dataset registry with explicit source and download provenance.
- Gzip edge-list parser with directed-to-undirected normalization for the current partitioning objective.
- Local dataset cache with SHA-256 provenance recorded in validation results.
- Four routine SNAP empirical reference graphs: C. elegans frontal, Florida Bay, S. cerevisiae, and email-Eu-core.
- Separate scalability registry for ca-GrQc, ca-HepTh, and Wiki-Vote.
- SNAP validation experiment with graph-level paired bootstrap analysis and leave-one-graph-out routing.
- Unit coverage for the SNAP parser, registries, and validation protocol without requiring network access.
- Manual live-data validation workflow under .github/workflows/snap-validation.yml.

### Methodology

- Third-party graph files are not vendored into the repository.
- The routine SNAP corpus and larger scalability corpus remain explicitly separated.
- Direction and signed semantics are normalized only for the current unweighted undirected partitioning objective; those original semantics are retained in dataset metadata.
- Downloaded dataset SHA-256 values are recorded in result manifests.

## 0.4.0 — 2026-09-21

### Added

- Standard external reference graph corpus using four empirical graphs exposed by NetworkX.
- External validation runner with the same two-way benchmark protocol used by the canonical suite.
- External graph-level paired bootstrap comparisons.
- External leave-one-graph-out routing evaluation with regret and oracle agreement.
- Explicit dataset provenance metadata and external result manifest.
- CI coverage for the external validation experiment.

### Methodology

- Synthetic development graphs and external reference graphs are kept as separate evidence layers.
- Repeated seeds remain aggregated within graph before bootstrap resampling.
- Edge weights are ignored in the external cross-strategy metric so that all compared methods share unweighted edge cut.
- The four-graph external corpus is treated as a reference test surface, not as a representative population sample.

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
