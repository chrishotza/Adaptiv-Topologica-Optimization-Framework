# ATOF: AI-first agent guide

ATOF is an open-source graph optimization interface with a stable machine contract, reproducible provenance, and an explicit separation between the ATOF Engine and ATOF Portfolio.

## First 30 seconds

1. Run `atof ai` for the stable machine contract.
2. Run `atof doctor` to inspect available engines and the runtime.
3. Run `atof solve examples/demo.edgelist` for the shortest practical portfolio path.
4. Use `--compact` when topology detail or node assignments are not required.
5. For k-way native Engine work, use `atof optimize <graph> --engine bloc --k <k>` with `k>=2`.
6. Use JSON input when a machine-friendly nodes/edges payload is already available.
7. Preserve `--seed` for reproducible experiments.
8. Use full JSON when topology, provenance, candidate detail, or partition mapping is required.

## Contract hierarchy

For machine-facing work, use this order:

1. `atof ai` — runtime capability and limit manifest;
2. `schemas/` — stable machine-readable response contracts;
3. `AGENTS.md` — operating rules for agents;
4. product docs — human-readable operational detail;
5. `research/` and `experiments/` — evidence/history, not product capability guarantees.

Do not infer current capabilities from historical research branches or frozen experiment results.

## Canonical commands

```bash
atof ai
atof doctor
atof solve examples/demo.edgelist
atof solve examples/demo.edgelist --partition-output partition.csv
atof profile examples/demo.edgelist --compact
atof optimize examples/demo.edgelist --engine portfolio --compact
atof optimize examples/demo.edgelist --engine portfolio --output result.json
```

## Product semantics

**ATOF Engine** is the native product path: topology profiling, heuristic regime description, and BLOC-RELOC refinement.

**ATOF Portfolio** is the empirical composition layer over the available BLOC, NetworkX, METIS, and KaHIP backends.

The Engine contract is k>=2, undirected, simple, unweighted balanced edge-cut partitioning.

The Portfolio contract is k=2 under the same graph/objective model.

Input formats are edge-list, JSON, GraphML, GEXF, and GML. stdin supports edge-list and JSON.

## Contract

- Default machine output is JSON.
- `atof.ai.v1` describes capabilities and limits.
- `atof.doctor.v1` describes backend availability and runtime.
- `atof.error.v1` describes structured CLI failures.
- Optional backend failures are reported rather than silently hidden.
- Full results include provenance suitable for agent-to-agent handoff.
- Unsupported directed and multigraph product inputs are rejected; source weight attributes are ignored under the current unweighted objective.
- JSON graph input uses `{nodes?: [...], edges: [[u, v], ...]}`.
- `schemas/`, `atof ai`, and `AGENTS.md` form the machine-facing contract; prefer those over prose examples.

## Claim discipline

Do not claim universal optimality, universal speed superiority, or universal ease-of-use against every competing system. State the graph/corpus, objective, protocol, and environment when making comparative claims.
