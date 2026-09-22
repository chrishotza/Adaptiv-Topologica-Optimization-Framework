# Architecture

ATOF has two product layers and a separate research/evidence layer.

```text
Input graph
    |
    v
ATOF Interface
    |
    +----------------------+
    |                      |
    v                      v
ATOF Engine          ATOF Portfolio
    |                      |
Topology profile      Common backend contract
Regime baseline             |
BLOC-RELOC          +-------+--------+--------+
    |               |       |        |        |
    |             BLOC   NetworkX  METIS    KaHIP
    |               |       |        |        |
    +---------------+-------+--------+--------+
                    |
                    v
          Validation + provenance
                    |
                    v
             JSON / partition map
```

## ATOF Interface

The interface is designed for both humans and AI agents.

The primary machine-facing commands are:

- `atof ai` — stable `atof.ai.v1` capability manifest;
- `atof doctor` — stable `atof.doctor.v1` environment report;
- `atof solve` — shortest practical portfolio path;
- `atof profile` — structural graph description;
- `atof optimize` — explicit engine and variant control.

## ATOF Engine

The Engine is ATOF's own product path.

### Topology profiler

`TopologyProfiler` converts an input graph into an interpretable structural profile. The profile is descriptive; it does not prove that a regime requires a particular strategy.

### Regime selector

`HeuristicRegimeSelector` is a transparent descriptive baseline. It is intentionally not presented as a universally validated meta-optimizer.

### BLOC-RELOC

`BLOCReloc` is the canonical local-refinement strategy in the public engine. It supports deterministic initialization, balance-preserving `k`-way moves for `k>=2`, baseline and degree-affinity variants, and optimization traces.

## ATOF Portfolio

Portfolio mode is the composition layer over several available engines.

The current common contract is deliberately narrow:

- undirected graph;
- simple graph;
- unweighted edges;
- two-way partitioning (`k=2`);
- balanced edge-cut objective.

Available candidates are reported explicitly. Optional backend failures are recorded instead of hidden.

Selection is empirical:

1. minimize observed edge cut;
2. prefer lower balance error;
3. prefer lower runtime;
4. prefer stable backend-name ordering.

This is a selection policy, not a proof of global optimality.

## Provenance

Product results can include:

- graph SHA-256 fingerprint;
- seed;
- iteration parameters;
- backend identity and version;
- portfolio selection policy;
- post-processing status;
- backend availability.

The provenance layer makes results suitable for reproducible automation and AI-to-tool handoff.

## Research layer

The research layer is intentionally separate from the public product contract.

It contains:

- benchmark runners;
- routing experiments;
- external and SNAP validation;
- statistical analysis;
- frozen research artifacts.

Research findings are not automatically product guarantees.
