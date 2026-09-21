# Adaptive Topological Optimization Framework (ATOF)

ATOF is a research framework for topology-aware graph optimization, regime detection, adaptive strategy selection, and reproducible benchmarking.

The central idea is practical:

> **Graph structure should inform which optimization strategy is applied.**

Rather than assuming one partitioning method is uniformly effective, ATOF profiles a graph, characterizes its structural regime, evaluates candidate strategies, and preserves the evidence needed to compare them.

## What you can do with ATOF

- Profile graphs with interpretable structural descriptors.
- Run BLOC-RELOC as a balanced local partition-refinement strategy.
- Compare baseline and degree-affinity objectives explicitly.
- Route strategies by topology with a transparent heuristic baseline.
- Run reproducible multi-seed experiments.
- Extend the framework with new strategies, regime detectors, and learned selectors.

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
  v
Regime Detection / Strategy Selection
  |
  +--> BLOC-RELOC
  +--> Future strategies
  |
  v
Validation & Benchmarking
  |
  v
Results + Metadata
~~~

## Public core

The first public release is a curated consolidation of the shared graph-optimization research line.

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

This generates raw benchmark records, environment metadata, and a grouped edge-cut summary under results/canonical/.

The initial development suite contains seven deterministic synthetic topology families.

The benchmark compares balanced baselines, BLOC-RELOC variants, and NetworkX Kernighan-Lin for two-way partitions.

See docs/benchmark-protocol.md for the exact protocol.

## Example

~~~python
import networkx as nx

from atof.selector import HeuristicRegimeSelector
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler

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

Read the architecture, methodology, benchmark protocol, reproducibility, provenance, and legacy findings documents before interpreting historical results.

## Status

The repository is the beginning of the canonical public ATOF codebase.

The immediate research milestone is a fresh benchmark campaign generated from this repository itself, using a fixed protocol, explicit baselines, multiple seeds, statistical analysis, and commit-level provenance.

## Limitations

Regime-aware selection is not assumed to be universally optimal. The included selector is a transparent heuristic baseline and must be evaluated on held-out benchmark data before being treated as a validated adaptive policy.

Historical benchmark numbers are not automatically equivalent to results from the cleaned public implementation.

## Citation

See CITATION.cff.

## License

MIT. See LICENSE.
