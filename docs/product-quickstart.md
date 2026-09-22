# Product quickstart

ATOF is an AI-first command-line and Python interface for reproducible graph profiling and two-way partitioning.

## Install

Core installation:

```bash
python -m pip install -e .
```

Optional METIS and KaHIP engines:

```bash
python -m pip install -e ".[metis,kahip]"
```

## AI-first path

```bash
atof ai
atof doctor
atof solve examples/demo.edgelist
```

The same CLI is available as a Python module:

```bash
python -m atof ai
python -m atof solve examples/demo.edgelist
```

Use this order when an AI agent is driving the tool:

1. discover the machine contract;
2. inspect the environment and backend availability;
3. solve with the shortest practical portfolio path.

## Profile

```bash
atof profile examples/demo.edgelist
atof profile examples/demo.edgelist --compact
```

Full profile output contains structural descriptors and the transparent regime recommendation. Compact output keeps graph size, recommendation, and provenance.

## ATOF Engine

Run ATOF's own BLOC-RELOC path:

```bash
atof optimize examples/demo.edgelist --engine bloc
```

Select a BLOC variant explicitly:

```bash
atof optimize examples/demo.edgelist --engine bloc --variant baseline
atof optimize examples/demo.edgelist --engine bloc --variant affinity
```

## ATOF Portfolio

Run the common backend contract:

```bash
atof solve examples/demo.edgelist
atof optimize examples/demo.edgelist --engine portfolio
atof optimize examples/demo.edgelist --engine portfolio --compact
```

Portfolio mode currently supports `k=2`, undirected simple graphs, and an unweighted edge-cut objective. It evaluates the available BLOC, NetworkX Kernighan-Lin, and optional METIS/KaHIP engines.

The selected result is the minimum observed edge cut under the common contract, with balance and runtime used as tie-breakers.

## Export a partition

```bash
atof solve examples/demo.edgelist --partition-output partition.csv
atof optimize examples/demo.edgelist --engine portfolio --partition-output partition.json
```

Supported mapping formats are JSON, CSV, and TSV.

## Reuse from Python

```python
import networkx as nx
from atof import optimize_graph, optimize_portfolio

graph = nx.path_graph(20)

engine_result = optimize_graph(graph, k=2, seed=42, iterations=25)
portfolio_result = optimize_portfolio(graph, k=2, seed=42, iterations=25)

print(engine_result.to_dict(include_partition=False))
print(portfolio_result.to_dict(include_partition=False))
```

## Input contract

The public product contract requires:

- undirected graphs;
- simple graphs;
- at least two nodes;
- unweighted edge-cut objective; edge `weight` attributes are accepted but ignored;
- supported formats: edge-list, GraphML, GEXF, GML.

Unsupported directed and multigraph inputs are rejected. Edge `weight` attributes are accepted as source metadata and ignored by the current unweighted objective.

## Provenance

Full product and portfolio results can include graph fingerprint, seed, parameters, backend identity/version, and selection policy.

## Claims

ATOF deliberately separates implementation capability from comparative interpretation.

Benchmark claims should name the graph or corpus, objective, protocol, environment, and measured result.

See [docs/claims.md](claims.md), [docs/architecture.md](architecture.md), and [docs/ai-quickstart.md](ai-quickstart.md).
