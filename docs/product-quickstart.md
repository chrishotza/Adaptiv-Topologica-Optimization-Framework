# Product quickstart

ATOF can be used as a small command-line tool on a whitespace-delimited edge-list graph.

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