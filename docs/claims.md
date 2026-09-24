# Product claims and evidence

This document is the source of truth for external claims about the public MVP. A claim belongs in marketing or the README only when the evidence level below supports it.

## Supported by implementation

### AI-first machine surface

ATOF exposes a compact machine contract through:

- atof ai
- atof doctor
- atof solve
- compact JSON output
- formal schemas under schemas/

These are implementation claims and are protected by unit tests and CLI tests.

### One interface over multiple open backends

Portfolio mode currently evaluates, when available:

- BLOC-RELOC;
- NetworkX Kernighan-Lin;
- METIS via PyMetis;
- KaHIP via KaFFPa-Strong;
- KaMinPar default and strong;
- Mt-KaHyPar default and quality.

The common product contract is balanced k-way partitioning on simple, undirected, unweighted graphs with edge cut as the shared reported objective.

### Reproducible handoff

Product and portfolio outputs can include:

- graph fingerprint;
- seed;
- iteration parameters;
- backend identity/version;
- selection policy;
- backend availability;
- postprocessing status.

This is a provenance claim, not a scientific performance claim.

### Downstream interoperability

The BLOC product path and the Portfolio/solve path export node-to-block mappings as JSON, CSV, or TSV through the same mapping writer.

## Benchmark-qualified claims

### Karate Club clean-environment result

In the clean GitHub Actions benchmark run on 2026-09-22, using Zachary's Karate Club graph (34 nodes, 78 edges), k=2 and an unweighted balanced edge-cut objective:

- ATOF Engine produced edge cut 39.
- ATOF Portfolio produced edge cut 10 and selected PyMetis.
- NetworkX Kernighan-Lin produced edge cut 10.
- METIS via PyMetis produced edge cut 10.
- KaHIP produced edge cut 10.
- All five methods reported balance error 0.

This supports a narrow claim: the current ATOF Portfolio can expose multiple open backends through one interface and, on this benchmark configuration, reach the same measured edge cut as the direct backends.

It does **not** support a speed claim. In the same run, direct NetworkX/METIS/KaHIP execution was substantially faster on this small graph, and ATOF Portfolio setup included the combined package surface.

This is evidence for one named graph, one protocol, one environment, and one objective—not a universal performance result.

### K=4 topology-routing generalization

In the final corrected GitHub Actions run on commit 72ba33ae2610a362eefa471def06d485244cc02d, the frozen research protocol evaluated 20 graphs, seeds 42/101/2024, and eight k=4 strategies using leave-one-corpus-out training.

The measured graph-level mean relative regret was:

- majority control: 3.408%;
- centroid topology router: 0.714%;
- nearest topology router: 0.445%.

Router-minus-majority paired bootstrap 95% confidence intervals were:

- centroid: [-6.356, -0.013] percentage points;
- nearest: [-6.617, -0.202] percentage points.

This supports a narrow research claim: under this fixed graph-partitioning corpus and protocol, topology-based routing retained measurable transfer value when moving from the earlier k=2 setting to genuine k=4 partitioning.

The claim is deliberately bounded. It does **not** establish cross-domain generalization, universal superiority, production readiness, or validity for arbitrary graph populations/objectives. The experiment made no production/default behavior change.

The artifact and workflow are the primary evidence. Interpret the result together with the frozen protocol, seed-stability record, and the repository's explicit uncertainty/promotion rules.

The clean-environment access benchmark measures setup, import, first-run time, repeat-run time, edge cut, balance, versions, and determinism separately for ATOF Engine, ATOF Portfolio, NetworkX, METIS, and KaHIP.

Do not summarize those measurements as a universal winner without a defined corpus and protocol. The Karate Club result above is the current concrete benchmark example.

## Open-source claim

The repository is MIT licensed. That supports the claim of zero software license cost for the code.

The product terminology is intentionally split: **ATOF Engine** means the native BLOC-RELOC product path; **ATOF Portfolio** means the composition layer over multiple available backends.

It does not imply:

- zero installation friction;
- zero runtime cost;
- universal algorithmic quality;
- universal ease of use.

Those properties are empirical and must be benchmarked.

## Claims explicitly not supported

ATOF should not claim:

- universally optimal graph partitions;
- universally faster execution than METIS, KaHIP, or NetworkX;
- universally easier setup than every competing graph optimizer;
- production readiness for every graph size, graph model, objective, or workload;
- superiority based only on open-source licensing;
- cross-domain adaptive-routing generality based on graph-partitioning experiments.

## Preferred language

Use:

> Open-source graph optimization with an AI-first machine interface, reproducible provenance, and a common portfolio layer over multiple backends.

For research findings use:

> On [named benchmark/corpus], under [named objective/protocol], [method] produced [measured result].

For the k=4 finding, the bounded formulation is:

> Under the frozen 20-graph k=4 protocol, topology-based routing showed lower graph-level relative regret than the majority control, with the reported bootstrap uncertainty shown explicitly.

Avoid:

> ATOF is better than everything else.

The repository is designed to make the first statements easy to verify and the second one unnecessary.
