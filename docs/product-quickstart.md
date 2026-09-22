# Product quickstart

ATOF is a small command-line and Python interface for graph profiling and two-way partitioning.

## Install

~~~bash
python -m pip install -e .
~~~

## AI-first path

~~~bash
atof ai
atof doctor
atof solve graph.edgelist
~~~

Use this order when an AI agent is driving the tool:

1. discover the machine contract;
2. inspect the environment and available backends;
3. solve with the shortest portfolio path.

## Profile

~~~bash
atof profile graph.edgelist
atof profile graph.edgelist --compact
~~~

Full profile output includes topology descriptors and a transparent heuristic recommendation. Compact output keeps only graph size, recommendation fields, and graph fingerprint.

## Optimize with BLOC-RELOC

~~~bash
atof optimize graph.edgelist --engine bloc
~~~

The default BLOC path uses the transparent heuristic selector and returns a machine-readable result with topology, move statistics, parameters, and provenance.

## Optimize with the open-source portfolio

~~~bash
atof solve graph.edgelist
atof optimize graph.edgelist --engine portfolio --compact
atof optimize graph.edgelist --engine portfolio
~~~

Portfolio mode currently supports k=2 and an unweighted edge-cut objective. It evaluates BLOC-RELOC, NetworkX Kernighan-Lin, and optional PyMetis/KaHIP backends when installed. Selection is empirical: lowest observed edge cut, then balance, runtime, and name as tie-breakers.

Optional backends:

~~~bash
python -m pip install -e ".[metis,kahip]"
~~~

Unavailable optional engines are reported rather than silently hidden.

## Reuse from Python

~~~python
import networkx as nx
from atof import optimize_graph, optimize_portfolio

graph = nx.path_graph(20)

bloc = optimize_graph(graph, k=2, seed=42, iterations=25)
portfolio = optimize_portfolio(graph, k=2, seed=42, iterations=25)

print(bloc.to_dict(include_partition=False))
print(portfolio.to_dict(include_partition=False))
~~~

## Input formats

The product loader supports edge-list, GraphML, GEXF, and GML. With format auto, GraphML/GEXF/GML are inferred from the file extension; other files default to edge-list parsing.

## Export the BLOC partition

~~~bash
atof optimize graph.edgelist --engine bloc --output result.json --partition-output partition.csv
~~~

Use --partition-format json or --partition-format tsv when needed. The exported mapping contains node and block fields.

## Contract and claims

ATOF deliberately separates implementation capability from comparative interpretation:

- portfolio is a practical composition layer, not a universal optimum claim;
- topology regime labels are descriptive heuristics;
- benchmark claims must name the graph, corpus, objective, and environment;
- full results preserve enough provenance for reproducible downstream use.

See docs/ai-quickstart.md, docs/open-source-access-benchmark.md, and docs/claims.md.
