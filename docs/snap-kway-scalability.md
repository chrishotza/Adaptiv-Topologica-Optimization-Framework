# SNAP k-way scalability evidence

## Protocol

The operational stress test runs the Portfolio contract on the larger SNAP scalability corpus:

- ca-GrQc
- ca-HepTh
- Wiki-Vote

For each graph it executes k=2, k=4, and k=8 with:

- seed 42
- iterations=5
- include_optional=true
- profile_mode=bounded

The test is an operational stress surface, not a quality-ranking benchmark.

## Validated run

Validated on 2026-09-24 through GitHub Actions run 36016128770 on commit 5a8f7f82d2d747ba4ee0d22bf4528b0c5bc4fabc.

Artifact:

- name: atof-snap-kway-scalability
- artifact ID: 10814886223
- SHA-256: 800c5078d456e1bdffe53240c3511f19d099a56c823a6c13cc6aa70a22accf81

The run completed all 9/9 graph×k cases successfully.

Total wall-clock runtime for the runner was 28.9559 s on the GitHub-hosted Linux runner.

The maximum selected-partition balance error across the nine cases was 0.00143075. The maximum candidate balance error observed anywhere in the manifest was 0.00171690.

Backend availability in this runner:

- BLOC and BLOC affinity: available in all 9 cases.
- KaMinPar default and strong: available in all 9 cases.
- Mt-KaHyPar default and quality: available in all 9 cases.
- NetworkX Kernighan-Lin: available for the 3 k=2 cases and correctly marked not applicable for k>2.
- METIS/PyMetis: unavailable because the optional package was not installed.
- KaHIP: unavailable because the optional package was not installed.

No case returned error.

## Scope

This evidence establishes that the bounded profiling path and the k-way Portfolio execution path complete end-to-end on the three larger empirical graphs under the tested environment. It does not establish universal performance, quality dominance, or behavior on arbitrary graph populations.
