# Architecture

ATOF separates graph description, strategy execution, adaptive routing, and evidence.

## Topology profiler

`TopologyProfiler` turns a graph into an interpretable structural profile. The profile is descriptive; it does not itself prove that a regime requires a particular strategy.

## Strategy layer

`BLOCReloc` is the canonical local-refinement strategy in the public core. It supports deterministic initialization, baseline cut, degree-affinity costs, balance-preserving node moves, optional sampled two-swaps, and iteration traces.

## Selector layer

`HeuristicRegimeSelector` is a transparent routing baseline. It is not a trained meta-selector and should not be presented as universally validated until benchmarked on held-out data.

## Benchmark layer

`benchmark_bloc` returns records containing graph, variant, seed, edge cut, weighted objective, balance error, and trace information.

## Evidence layer

Canonical implementation and historical evidence remain separate so exploratory artifacts do not silently become validation claims.
