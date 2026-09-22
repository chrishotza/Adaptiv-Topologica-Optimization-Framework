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
- KaHIP via KaFFPa-Strong.

The common product contract is currently k=2, unweighted, undirected edge cut with balance reported explicitly.

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

The BLOC product path and the portfolio/solve path export node-to-block mappings as JSON, CSV, or TSV through the same mapping writer.

## Benchmark-qualified claims

### Karate Club clean-environment result

In the clean GitHub Actions benchmark run on 2026-09-22, using Zachary's Karate Club graph (34 nodes, 78 edges), k=2 and an unweighted balanced edge-cut objective:

- ATOF core produced edge cut 39.
- ATOF portfolio produced edge cut 10 and selected PyMetis.
- NetworkX Kernighan-Lin produced edge cut 10.
- METIS via PyMetis produced edge cut 10.
- KaHIP produced edge cut 10.
- All five methods reported balance error 0.

This supports a narrow claim: the current ATOF portfolio can expose multiple open backends through one interface and, on this benchmark configuration, reach the same measured edge cut as the direct backends.

It does **not** support a speed claim. In the same run, direct NetworkX/METIS/KaHIP execution was substantially faster on this small graph, and ATOF portfolio setup included the combined package surface.

This is evidence for one named graph, one protocol, one environment, and one objective—not a universal performance result.

The clean-environment access benchmark measures setup, import, first-run time, repeat-run time, edge cut, balance, versions, and determinism separately for ATOF core, ATOF portfolio, NetworkX, METIS, and KaHIP.

Do not summarize those measurements as a universal winner without a defined corpus and protocol. The Karate Club result above is the current concrete benchmark example.

## Open-source claim

The repository is MIT licensed. That supports the claim of zero software license cost for the code.

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
- superiority based only on open-source licensing.

## Preferred language

Use:

> Open-source graph optimization with an AI-first machine interface, reproducible provenance, and a common portfolio layer over multiple backends.

Use comparative language only in the form:

> On [named benchmark/corpus], under [named objective/protocol], ATOF produced [measured result].

Avoid:

> ATOF is better than everything else.

The repository is designed to make the first statement easy to verify and the second one unnecessary.
