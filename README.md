# Adaptive Topological Optimization Framework (ATOF)

ATOF is a research framework for topology-aware graph optimization, regime detection, adaptive strategy selection, and reproducible benchmarking.

The central idea is practical:

> **Graph structure should inform which optimization strategy is applied.**

Rather than assuming one partitioning method is uniformly effective, ATOF profiles a graph, characterizes its structural regime, evaluates candidate strategies, and preserves the evidence needed to compare them.

## What you can do with ATOF

- Profile graphs with interpretable structural descriptors.
- Run BLOC-RELOC as a balanced local partition-refinement strategy.
- Compare baseline and degree-affinity objectives explicitly.
- Route strategies by topology with a transparent heuristic or graph-level learned baseline.
- Inspect optimization dynamics from accepted/rejected move traces.
- Run reproducible multi-seed experiments, held-out routing evaluations, graph-aware uncertainty analysis, and external reference-corpus validation.

## Architecture

~~~text
Graph
  |
  v
Topology Profiler
  |
  v
Structural Representation
  |
  +--> Regime Detection
  |
  +--> Strategy Routing
  |      +--> Heuristic selector
  |      +--> Learned topology router
  |
  +--> BLOC-RELOC
  +--> Other benchmark strategies
  |
  v
Validation
  |
  +--> Canonical benchmark
  +--> Dynamics observatory
  +--> Graph-level holdout
  +--> Graph-level uncertainty
  |
  v
Results + Metadata
~~~

## Public core

The public repository is a curated consolidation of the shared graph-optimization research line.

The topology profiling layer comes from the former adaptive-topological-optimization repository.

The BLOC-RELOC refinement engine and dynamics-analysis lessons come from bloc-reloc-v2.

Reproducibility and provenance rules were extracted from the broader research archive.

COV-IA remains a separate prototype. Its adaptive-control ideas are documented as a boundary case rather than mixed into the graph-optimization core.

## Quick start

~~~bash
python -m pip install -e ".[dev]"
pytest
python examples/basic_usage.py
~~~

## Run the canonical benchmark

~~~bash
python -m experiments.run_canonical
python -m experiments.summarize_results
~~~

This generates raw benchmark records, environment metadata, benchmark commit provenance when available, and a grouped edge-cut summary under results/canonical/.

The initial development suite contains seven deterministic synthetic topology families.

The benchmark compares balanced baselines, BLOC-RELOC variants, and NetworkX Kernighan-Lin for two-way partitions.

See docs/benchmark-protocol.md for the exact protocol.

## Run the dynamics observatory

~~~bash
python -m experiments.run_observatory
~~~

The observatory preserves topology, regime, strategy, seed, final metrics, and trace-derived activity statistics under results/observatory/.

See docs/dynamics.md and docs/statistical-analysis.md.

## Run graph-level routing evaluation

~~~bash
python -m experiments.run_routing_evaluation
~~~

The routing evaluation uses **leave-one-graph-out** validation. The held-out graph's seeds are not used to train the topology router.

It compares:

- a fixed global-strategy baseline;
- the transparent heuristic selector;
- the learned topology router;
- the post-hoc graph-level oracle.

Primary routing metrics are oracle agreement and graph-level regret.

See docs/routing-evaluation.md.

## Run graph-aware statistical analysis

~~~bash
python -m experiments.run_statistical_analysis
~~~

The statistical layer aggregates repeated seeds within each graph and then bootstraps the graph-level paired differences. It reports mean differences, 95% percentile bootstrap intervals, graph-level wins/losses/ties, and a standardized paired effect.

This is uncertainty quantification for the current synthetic development suite, not evidence of universal generalization.

See docs/statistical-analysis.md.

## Run external reference validation

~~~bash
python -m experiments.run_external_validation
~~~

This runs the same two-way benchmark protocol over four standard reference graphs exposed by NetworkX: Zachary's Karate Club, Davis Southern Women, Florentine Families, and Les Misérables.

The experiment records dataset provenance, topology, benchmark rows, graph-level paired bootstrap comparisons, and leave-one-graph-out routing regret under results/external/.

This corpus is an **external reference validation layer**, not a representative sample of all graph populations. The graphs are small and heterogeneous, and the unweighted edge-cut metric is used consistently for cross-strategy comparison.

See docs/external-validation.md.

## Example

~~~python
import networkx as nx

from atof.routing import LearnedTopologyRouter
from atof.topology import TopologyProfiler
from atof.selector import HeuristicRegimeSelector
from atof.strategies import BLOCReloc

graph = nx.barabasi_albert_graph(100, 3, seed=42)

profile = TopologyProfiler().profile(graph)
recommendation = HeuristicRegimeSelector().recommend(profile)

result = BLOCReloc(
    graph,
    k=4,
    seed=42,
    variant="affinity",
).refine(iterations=10)

print(recommendation.regime)
print(result.edge_cut)
~~~

## Research discipline

ATOF deliberately separates:

1. **method** — what the implementation does;
2. **measurement** — how performance is evaluated;
3. **evidence** — which experiment generated a result;
4. **interpretation** — what the result may mean.

Historical experiments are therefore labeled as historical rather than silently presented as validation of the cleaned public implementation.

Routing is evaluated at the graph level so that repeated seeds from one graph do not become artificial independent training examples.

Statistical uncertainty is also evaluated at graph level, preserving the unit on which topology generalization is actually claimed.

## Status

Version 0.4.0 is the current public research baseline.

The repository now contains a canonical benchmark, trace dynamics, a descriptive observatory, graph-level held-out routing, graph-aware statistical uncertainty, and an external reference validation layer.

Further research should expand the external corpus substantially, add stronger canonical baselines, pre-specify comparison families, and quantify routing generalization on larger unseen graph populations.

## Limitations

The learned router is a transparent nearest-centroid baseline, not a final meta-learning architecture.

The synthetic benchmark suite is a development and regression suite, not evidence of universal superiority over graph-partitioning literature.

The bootstrap intervals on the synthetic suite and the external reference corpus are conditional on those small corpora and should not be interpreted as population-level confidence for arbitrary graphs.

Historical benchmark numbers are not automatically equivalent to results from the cleaned public implementation.

## Citation

See CITATION.cff.

## License

MIT. See LICENSE.
