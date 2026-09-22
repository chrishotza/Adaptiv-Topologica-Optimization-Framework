# AI-first interface

ATOF exposes a deliberately small machine-facing surface so an AI agent can enter the repository, understand the contract, and act without reading the entire research history.

## 1. Ask the repository what it is

~~~bash
atof ai
~~~

The command returns compact JSON using schema atof.ai.v1. Use "atof ai --full" for the expanded manifest.

## 2. Inspect a graph

~~~bash
atof profile graph.edgelist --compact
~~~

This is the low-token path when an agent needs graph size and the current structural recommendation.

## 3. Produce a practical partition

~~~bash
atof optimize graph.edgelist --engine portfolio --compact
~~~

Portfolio mode evaluates the available open-source backends under the same current contract: balanced, unweighted, two-way edge cut. Optional METIS and KaHIP backends are used when their dependencies are installed.

## 4. Ask for complete evidence

~~~bash
atof optimize graph.edgelist --engine portfolio
~~~

Use full output when the agent needs topology descriptors or the node-to-block mapping. For programmatic pipelines, write JSON to a file with --output.

## Token discipline

- Start with "atof ai"; do not ingest the whole README when the task is operational.
- Use "--compact" for routing, orchestration, summaries, and tool-to-tool handoff.
- Use full output only for topology analysis or partition inspection.
- Prefer stable field names over scraping CLI prose.
- Preserve seed in experiments that must be reproducible.

## Machine contract

The current compact result focuses on:

~~~text
mode
version
graph.nodes
graph.edges
strategy
result.k
result.edge_cut
result.balance_error
candidates[] (portfolio mode)
~~~

This contract is intentionally narrower than the research schema. The research artifacts remain the source of truth for scientific evaluation.
