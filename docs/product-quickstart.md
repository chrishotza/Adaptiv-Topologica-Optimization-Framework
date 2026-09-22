# Product quickstart

ATOF can be used as a small command-line tool on a whitespace-delimited edge-list graph.

## AI-first usage

For an AI agent, start with the smallest stable contract:

~~~bash
atof ai
atof profile graph.edgelist --compact
atof optimize graph.edgelist --engine portfolio --compact
~~~

Use atof ai --full only when the agent needs the complete capability manifest. Compact results omit topology detail and node-to-block mappings to reduce context size. See AGENTS.md and docs/ai-quickstart.md.

## Install

~~~bash
python -m pip install -e .
~~~

## Profile a graph

~~~bash
atof profile graph.edgelist
~~~

This returns graph size, topology descriptors, and the transparent heuristic regime recommendation as JSON.

## Optimize a graph

~~~bash
atof optimize graph.edgelist
~~~

By default this:

1. profiles the graph;
2. uses the transparent heuristic selector to choose between the public BLOC-RELOC baseline and affinity variants;
3. runs a balanced 2-way partition for 25 iterations;
4. returns the selected strategy, edge cut, balance, move statistics, and the partition mapping.

For reproducible explicit runs:

~~~bash
atof optimize graph.edgelist --k 2 --seed 42 --iterations 25 --variant baseline
~~~

Save a machine-readable result:

~~~bash
atof optimize graph.edgelist --output result.json
~~~

## Product contract

The `auto` mode is deliberately described as a **heuristic selector**. It is not presented as a universally validated optimizer or as proof that the chosen strategy is globally optimal.

The optimization result is a balanced partition under ATOF's current BLOC-RELOC objective. The JSON result is intended to be easy to consume from another program or pipeline.

Research benchmarks and validation workflows remain separate from this product entry point.
## Reuse from Python

~~~python
import networkx as nx
from atof import optimize_graph

graph = nx.path_graph(20)
result = optimize_graph(graph, k=2, seed=42, iterations=25)
print(result.partition_result.edge_cut)
~~~

The reusable API returns both the topology profile and the partition result. Call `result.to_dict(include_partition=False)` when the full node-to-block mapping is not needed.

## Input formats

The product loader supports `edgelist`, `graphml`, `gexf`, and `gml`. With `--format auto`, GraphML/GEXF/GML are detected from the file extension; other files default to edge-list parsing.

## Portfolio mode

ATOF can act as an open-source portfolio layer over several graph partitioning backends.

~~~bash
atof optimize graph.edgelist --engine portfolio
~~~

Portfolio mode evaluates the internal BLOC-RELOC variants and NetworkX Kernighan-Lin. When the optional extras are installed, it also evaluates PyMetis and KaHIP. The selected result is the lowest edge cut among available candidates under the same two-way balance contract.

Optional backends remain optional:

~~~bash
python -m pip install -e ".[dev,metis,kahip]"
~~~

The JSON output records which candidates were available, the edge cut, balance error, runtime, and any unavailable-backend reason. Portfolio mode is an empirical selection mechanism, not a claim of universal optimality.
