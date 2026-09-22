# ATOF — Adaptive Topological Optimization Framework

> **AI-first, open-source graph optimization with a common interface, reproducible provenance, and optional backend composition.**

[![CI](https://github.com/chrishotza/Adaptiv-Topologica-Optimization-Framework/actions/workflows/ci.yml/badge.svg)](https://github.com/chrishotza/Adaptiv-Topologica-Optimization-Framework/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](pyproject.toml)

**ATOF** gives humans and AI agents one machine-readable path to profile a graph, inspect available optimization engines, run a reproducible two-way partition, and export the result.

Maintained by **Chris Hotza — Investigador Independiente**.

## Start in 30 seconds

Install the core:

```bash
python -m pip install -e .
```

Ask ATOF what it can do:

```bash
atof ai
```

Inspect the environment:

```bash
atof doctor
```

Run the shortest practical AI path:

```bash
atof solve examples/demo.edgelist
```

The same CLI is available as a Python module:

```bash
python -m atof ai
python -m atof solve examples/demo.edgelist
```

Pipe an edge-list directly when the graph already exists in a shell or agent pipeline:

```bash
cat graph.edgelist | atof solve -
```

Request the partition mapping:

```bash
atof solve examples/demo.edgelist --partition-output partition.csv
```

For the optional METIS and KaHIP backends:

```bash
python -m pip install -e ".[metis,kahip]"
```

## Why ATOF

ATOF is built around a simple interface problem:

- graph optimizers often expose different APIs, inputs, outputs, and dependency requirements;
- AI agents need small, explicit, machine-readable contracts;
- benchmark claims need provenance instead of hand-written summaries.

ATOF provides one surface over a small portfolio of open backends and keeps the evidence boundary explicit.

## Product architecture

```text
                         ATOF
                          |
              +-----------+-----------+
              |                       |
        ATOF Engine              ATOF Portfolio
        BLOC-RELOC          empirical backend composition
              |                       |
              |          +------------+-------------+
              |          |            |             |
              |        BLOC       NetworkX       METIS / KaHIP
              |                       |
              +-----------+-----------+
                          |
                  JSON + provenance
                          |
                 partition export
```

### ATOF Engine

The engine is ATOF's own product path:

- topology profiling;
- transparent regime recommendation;
- BLOC-RELOC balanced local refinement;
- deterministic seeds and machine-readable results.

The heuristic regime selector is a **descriptive baseline**, not a universal optimizer.

### ATOF Portfolio

The portfolio is the composition layer:

- BLOC-RELOC baseline;
- BLOC-RELOC affinity;
- NetworkX Kernighan-Lin;
- METIS via PyMetis, when installed;
- KaHIP via KaFFPa-Strong, when installed.

The current portfolio contract is intentionally narrow: **k=2, undirected, simple, unweighted graphs, minimizing balanced edge cut**.

Selection is empirical: lowest observed edge cut, then balance, runtime, and backend name as tie-breakers.

## AI-first interface

The machine-facing surface is deliberately small:

```bash
atof ai
atof doctor
atof solve graph.edgelist
atof profile graph.edgelist --compact
atof optimize graph.edgelist --engine portfolio --compact
```

The stable contracts are:

- `atof.ai.v1` — capabilities and limits;
- `atof.doctor.v1` — environment and backend availability;
- `schemas/` — machine-readable contract definitions.

Use `--compact` for low-token orchestration. Use full JSON when topology, provenance, candidate details, or the node-to-block mapping is needed.

## Reproducibility

Product results carry machine-readable provenance including:

- graph SHA-256 fingerprint;
- seed and iteration parameters;
- selected backend;
- backend availability and versions;
- portfolio selection policy;
- post-processing information where applicable.

This makes the output suitable for downstream automation and agent-to-agent handoff.

## Partition export

The same node-to-block mapping can be written as JSON, CSV, or TSV:

```bash
atof solve graph.edgelist --partition-output partition.csv
atof optimize graph.edgelist --engine portfolio --partition-output partition.json
```

## Current evidence

The current clean-environment access benchmark used Zachary's Karate Club graph (34 nodes, 78 edges), k=2, balanced unweighted edge cut:

| Path | Edge cut | Balance error | First partition |
|---|---:|---:|---:|
| ATOF Engine | 39 | 0.0 | 0.0751 s |
| ATOF Portfolio | 10 | 0.0 | 0.0771 s |
| NetworkX Kernighan-Lin | 10 | 0.0 | 0.000895 s |
| METIS | 10 | 0.0 | 0.000396 s |
| KaHIP | 10 | 0.0 | 0.01249 s |

On that run, ATOF Portfolio selected PyMetis.

This is a **benchmark-qualified composition/access result**, not a universal optimality or speed claim. Direct backends were faster on this small graph.

See [docs/claims.md](docs/claims.md) and [docs/open-source-access-benchmark.md](docs/open-source-access-benchmark.md).

## Current MVP contract

| Area | Current contract |
|---|---|
| Graph model | undirected, simple |
| Objective | balanced unweighted edge cut |
| Partitioning | 2-way (`k=2`) |
| Input | edge-list, GraphML, GEXF, GML |
| Output | JSON + JSON/CSV/TSV partition mapping |
| Optional engines | METIS / KaHIP |
| Evidence | reproducible provenance + benchmark-qualified claims |

Weighted and multiway portfolio optimization are intentionally outside the current MVP contract.

## Repository map

```text
src/atof/       Product and research implementation
tests/          Automated regression and contract tests
docs/           Product, protocol, architecture, and evidence docs
examples/       Tiny runnable examples
experiments/    Reproducible benchmark runners
research/       Frozen findings and historical evidence
schemas/        AI-facing JSON schemas
.github/        CI and benchmark workflows
```

Research material is preserved, but the **product surface is intentionally separate from the research archive**.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

Run the product path locally:

```bash
atof ai
atof doctor
atof solve examples/demo.edgelist
```

Run the research suite separately when needed:

```bash
python -m experiments.run_canonical
python -m experiments.run_observatory
python -m experiments.run_routing_evaluation
```

Research commands write generated outputs to ignored runtime directories.

## Evidence discipline

ATOF separates:

1. **method** — what the implementation does;
2. **measurement** — how it is benchmarked;
3. **evidence** — which run produced a result;
4. **interpretation** — what can responsibly be claimed.

Comparative statements should name the graph or corpus, objective, protocol, environment, and measured result.

## Learn more

- [AI-first guide](docs/ai-quickstart.md)
- [Product quickstart](docs/product-quickstart.md)
- [Architecture](docs/architecture.md)
- [Claims and evidence](docs/claims.md)
- [Open-source access benchmark](docs/open-source-access-benchmark.md)
- [Benchmark protocol](docs/benchmark-protocol.md)
- [Research findings](research/generalization-findings-2026-09-21.md)
- [AI agent rules](AGENTS.md)
- [llms.txt](llms.txt)

## Citation

See [CITATION.cff](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE).
