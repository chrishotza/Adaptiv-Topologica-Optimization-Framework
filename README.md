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
- Run reproducible multi-seed experiments, held-out routing evaluations, graph-aware uncertainty analysis, external reference-corpus validation, and cross-corpus routing summaries.

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
  +--> External reference corpora
  +--> Cross-corpus generalization summary
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
python -m pip install -e .
atof profile graph.edgelist
atof optimize graph.edgelist --output result.json
~~~

For development and the full test suite:

~~~bash
python -m pip install -e ".[dev]"
pytest
~~~

## AI-first entry point

ATOF is designed to be easy for AI agents to understand and operate with minimal context.

~~~bash
atof ai
atof solve graph.edgelist
atof profile graph.edgelist --compact
atof optimize graph.edgelist --engine portfolio --compact
~~~

The AI manifest uses the stable schema atof.ai.v1. Compact outputs intentionally omit verbose topology and partition mappings; full JSON remains available when evidence or node assignments are required. See AGENTS.md, docs/ai-quickstart.md, and llms.txt.

## Product entry point

The primary usable entry point is the `atof optimize` command. It profiles an edge-list graph, applies the transparent heuristic selector when `--variant auto` is used, runs balanced BLOC-RELOC refinement, and returns a machine-readable partition result. The selector is explicitly a heuristic baseline; the command does not claim global optimality. See `docs/product-quickstart.md`.

## Run the canonical benchmark

~~~bash
python -m experiments.run_canonical
python -m experiments.summarize_results
~~~

This generates raw benchmark records, environment metadata, benchmark commit provenance when available, and a grouped edge-cut summary under results/canonical/.

The initial development suite contains seven deterministic synthetic topology families.

The benchmark compares balanced baselines, BLOC-RELOC variants, a deterministic spectral bisection reference, and NetworkX Kernighan-Lin for two-way partitions.

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

## Run SNAP empirical validation

~~~bash
python -m experiments.run_snap_validation
~~~

ATOF 0.5.0 adds a live-data validation layer for six empirical SNAP graphs: C. elegans frontal, Florida Bay, S. cerevisiae transcriptional regulation, email-Eu-core, CollegeMsg, and reachability.

The runner downloads the public gzip edge lists only when needed, caches them locally, records SHA-256 provenance, normalizes the source graph to the undirected connectivity used by the current partition objective, and writes results to results/snap/.

A separate registry exposes larger graphs for scalability studies: ca-GrQc, ca-HepTh, and Wiki-Vote. These are intentionally excluded from the routine corpus because they are materially larger and should be treated as a distinct scalability/generalization tier.

The live SNAP workflow is manually triggerable from GitHub Actions.

See docs/snap-corpus.md.

## Cross-corpus generalization

The `atof.generalization` layer provides graph-level routing summaries across independent corpora.

### Run the aligned study

~~~bash
python -m experiments.run_generalization_study
~~~

This evaluates the common k=2 candidate set across development, external, and routine SNAP corpora.

### Run true corpus transfer

~~~bash
python -m experiments.run_cross_corpus_transfer
~~~

This excludes the complete test corpus from router training.

The transfer study compares:

- nearest-centroid topology router;
- 1-nearest-neighbor topology router;
- majority-oracle control;
- transparent heuristic selector.

The common seven-strategy candidate set is:

- round-robin balanced;
- random balanced;
- BLOC-RELOC baseline;
- BLOC-RELOC affinity;
- spectral bisection;
- balanced spectral-modularity bisection;
- NetworkX Kernighan-Lin.

The latest expanded 17-graph leave-one-corpus-out transfer (workflow `35574236663`) gives macro mean relative regret of **2.6916** for centroid, **0.7744** for 1-NN, **0.3242** for majority, and **6.2147** for the heuristic. Macro oracle agreement is **0.4444**, **0.4603**, **0.7381**, and **0.0833**, respectively.

These are descriptive results on the current corpus, not a universal routing claim.

See `docs/generalization-study.md` and `research/generalization-findings-2026-09-21.md`.

## Topology feature ablation

ATOF includes a reproducible leave-one-corpus-out feature ablation:

~~~bash
python -m experiments.run_feature_ablation
~~~

The current 17-graph scaling ablation shows that topology representation and distance scaling materially change transfer performance. The best observed centroid configuration was **global-path features + IQR scaling + L2 distance (0.4893 mean relative regret)**. The best observed 1-NN configurations were global-path + min-max/std + L2 (**0.5757**). The majority control remained at **0.3242**, so these are locked confirmatory candidates rather than a new default router.

See `docs/generalization-study.md` and `research/generalization-findings-2026-09-21.md`.

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

Version 0.6.0 is the current public product baseline. The CLI now provides a direct profile-and-optimize workflow while the benchmark/research layer remains reproducible and separately documented.

The repository now contains a canonical benchmark, trace dynamics, a descriptive observatory, graph-level held-out routing, graph-aware statistical uncertainty, NetworkX reference validation, a reproducible SNAP empirical corpus, and cross-corpus routing aggregation infrastructure.

The current research phase is focused on oracle-label stability and locked confirmation of the pre-specified routing candidates. The next decision should depend on those results rather than additional post-hoc feature tuning. Larger SNAP scalability studies and stronger canonical baselines remain separate future evidence tiers.

## Limitations

The learned router is a transparent nearest-centroid baseline, not a final meta-learning architecture.

The synthetic benchmark suite is a development and regression suite, not evidence of universal superiority over graph-partitioning literature.

The bootstrap intervals on the synthetic suite and the external reference corpus are conditional on those small corpora and should not be interpreted as population-level confidence for arbitrary graphs.

Historical benchmark numbers are not automatically equivalent to results from the cleaned public implementation.

## Citation

See CITATION.cff.

## License

MIT. See LICENSE.
