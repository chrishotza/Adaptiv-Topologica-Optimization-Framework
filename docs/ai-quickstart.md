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

Returns backend availability, versions, input formats, and a compact runtime summary. Its `portfolio_kway_ready` field tells an agent whether the current environment has at least one k-way-capable Portfolio backend that is actually importable. Each backend also reports `available` (package installed) separately from `importable` (Python/native module loads successfully). Use `atof doctor --probe` when the agent needs a real execution check on a tiny graph; each backend gets an operational result without requiring the agent to parse logs. Use `atof doctor --full` for the expanded environment record and `portfolio_kway_backends` list.

## 3. Fast solve

~~~bash
atof solve graph.edgelist
atof solve graph.edgelist --k 4
atof solve graph.edgelist --partition-output partition.csv
~~~

This is the shortest practical path: portfolio optimization, `k=2` by default, with `--k N` available for balanced k-way runs, compact JSON output, default seed 42.

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
atof optimize graph.edgelist --engine bloc --hybrid --compact
~~~

Use Engine mode when the task needs more than two balanced blocks. Add `--hybrid` when a deeper local refinement pass is appropriate; its benchmarked defaults are 5-iteration intervals and 100 two-node swap samples. Portfolio mode supports `k>=2`. NetworkX Kernighan-Lin is available only for `k=2`; BLOC-RELOC, METIS, KaHIP, KaMinPar, and Mt-KaHyPar can serve k-way requests when their backend is available.

## 8. Compare native Engine and Portfolio

~~~bash
atof compare graph.edgelist
atof compare graph.edgelist --k 4 --compact
~~~

Use this when an agent needs both ATOF's native Engine and the empirical Portfolio under identical parameters. The response is identified as `atof.compare.v1` and reports observed edge-cut and balance deltas without claiming global optimality.

## 8. Full evidence

~~~bash
atof optimize graph.edgelist --engine portfolio
atof optimize graph.edgelist --engine portfolio --k 4
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
objective.optimization_metric (Engine mode)
provenance.graph_fingerprint
candidates[] (Portfolio mode)

Portfolio responses identify themselves with `schema: "atof.portfolio.v1"`; Engine responses use `schema: "atof.optimize.v1"`; comparison responses use `schema: "atof.compare.v1"`. Full responses may include the selected `result.partition`; compact responses intentionally omit that field.
~~~

Machine-facing hierarchy: use `atof ai` for current capabilities and limits, `schemas/` for stable response shapes, and `AGENTS.md` for agent operating rules. Research and historical experiment material is evidence, not a capability contract.


## Structured errors

Invalid paths and unsupported product inputs return a machine-readable `atof.error.v1` response instead of requiring an agent to parse a traceback. See `schemas/atof-error-v1.schema.json`.
