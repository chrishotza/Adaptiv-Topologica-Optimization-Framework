# Product quickstart

ATOF is an AI-first command-line and Python interface for reproducible graph profiling and balanced graph partitioning.

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

## Pipe an edge-list through stdin

```bash
printf "a b\nb c\nc d\n" | atof solve -
```

Use `-` as the graph path for shell pipelines. stdin accepts edge-list or JSON when `--format json` is explicit. GraphML, GEXF, and GML use file paths.

## JSON input

A JSON graph uses `nodes` and `edges`:

```json
{"nodes":["a","b","isolated"],"edges":[["a","b"]]}
```

The `nodes` array preserves isolated nodes. The `edges` array contains 2-item node-ID arrays.

```bash
atof solve graph.json
printf '{"nodes":["a","b"],"edges":[["a","b"]]}' | atof solve - --format json
```

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

Engine variant semantics are explicit:

- `baseline` directly minimizes unweighted edge cut;
- `affinity` minimizes a degree-affinity weighted surrogate while reporting unweighted `edge_cut`;
- `auto` heuristically chooses between those variants.

Use `objective.optimization_metric` to identify what the Engine actually optimized.

## ATOF Engine with k-way partitioning

The native Engine supports `k>=2`:

```bash
atof optimize examples/demo.edgelist --engine bloc --k 4
```

The Engine keeps balanced node counts across the requested blocks. The reported comparison metric remains unweighted edge cut.

## ATOF Portfolio

Run the common backend contract:

```bash
atof solve examples/demo.edgelist
atof optimize examples/demo.edgelist --engine portfolio
atof optimize examples/demo.edgelist --engine portfolio --compact
```

Portfolio mode currently supports `k=2`, undirected simple graphs, and an unweighted edge-cut objective. For `k>2`, use the native Engine. It evaluates the available BLOC, NetworkX Kernighan-Lin, and optional METIS/KaHIP engines.

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
- unweighted graph model; edge `weight` attributes are accepted but ignored;
- supported formats: edge-list, JSON, GraphML, GEXF, GML.

Unsupported directed and multigraph inputs are rejected. Edge `weight` attributes are accepted as source metadata and ignored by the current graph model.

## Provenance

Full product and portfolio results can include graph fingerprint, seed, parameters, backend identity/version, and selection policy.

Engine results additionally expose:

- `objective.reported_metric`;
- `objective.optimization_metric`;
- variant-specific objective semantics.

## Claims

ATOF deliberately separates implementation capability from comparative interpretation.

Benchmark claims should name the graph or corpus, objective, protocol, environment, and measured result.

See [docs/claims.md](claims.md), [docs/architecture.md](architecture.md), and [docs/ai-quickstart.md](ai-quickstart.md).
