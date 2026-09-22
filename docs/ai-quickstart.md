# AI-first interface

ATOF exposes a small machine-facing surface so an AI agent can understand the tool, inspect its environment, solve a graph, and request deeper evidence without reading the entire research archive.

## 1. Discover

~~~bash
atof ai
~~~

Returns the compact atof.ai.v1 manifest.

## 2. Inspect the runtime

~~~bash
atof doctor
~~~

Returns backend availability, versions, input formats, and a compact runtime summary. Use "atof doctor --full" for the expanded environment record.

## 3. Fast solve

~~~bash
atof solve graph.edgelist
atof solve graph.edgelist --partition-output partition.csv
~~~

This is the shortest practical path: portfolio optimization, k=2, compact JSON output, default seed 42.

## 4. Pipe a graph directly

~~~bash
printf "a b\nb c\nc d\n" | atof solve -
~~~

Use `-` when the graph is already available to a shell pipeline or AI-controlled process. stdin accepts edge-list or JSON with `--format json`; use a file path for GraphML, GEXF, or GML.

## 5. Send JSON directly

~~~bash
printf '{"nodes":["a","b"],"edges":[["a","b"]]}' | atof solve - --format json
~~~

The minimal JSON contract is `nodes` (optional for edge-only graphs) plus `edges` (2-item node-ID arrays).

## 6. Inspect a graph

~~~bash
atof profile graph.edgelist --compact
~~~

Use this when the agent needs graph size and structural recommendation without the full topology descriptor set.

## 7. k-way Engine mode

~~~bash
atof optimize graph.edgelist --engine bloc --k 4 --compact
~~~

Use Engine mode when the task needs more than two balanced blocks. Portfolio mode remains `k=2`.

## 8. Full evidence

~~~bash
atof optimize graph.edgelist --engine portfolio
~~~

Full output includes candidate results, topology, provenance, and the selected node-to-block mapping.

## Token discipline

- Start with atof ai; do not ingest the whole README for operational tasks.
- Use atof doctor instead of guessing which optional engines are installed.
- Use --compact for orchestration and tool-to-tool handoff.
- Use full output only when topology, provenance, or partition assignments are required.
- Preserve the seed and graph fingerprint in experiment records.

## Machine contract

The compact result focuses on:

~~~text
mode
version
graph.nodes
graph.edges
strategy
parameters
result.k
result.edge_cut
result.balance_error
provenance.graph_fingerprint
candidates[] (Portfolio mode)
~~~

atof.ai.v1, atof.doctor.v1, and the JSON schemas under schemas/ are the machine-facing source of truth.


## Structured errors

Invalid paths and unsupported product inputs return a machine-readable `atof.error.v1` response instead of requiring an agent to parse a traceback. See `schemas/atof-error-v1.schema.json`.
