# Adaptive Topological Optimization Framework (ATOF)

ATOF is a research framework for topology-aware graph optimization, regime detection, adaptive strategy selection, and reproducible benchmarking.

The project is built around a practical idea:

> graph structure should inform which optimization strategy is applied.

Rather than assuming one partitioning method is uniformly effective, ATOF profiles a graph, characterizes its structural regime, evaluates candidate strategies, and records the evidence needed to compare them.

## What this repository provides

- **Topology profiling** — structural descriptors such as degree heterogeneity, clustering, assortativity, core structure, path metrics, and community structure.
- **BLOC-RELOC strategy** — a clean, reusable local partition-refinement implementation derived from the research prototype.
- **Adaptive selection** — transparent regime-aware strategy routing that can be extended with learned selectors.
- **Benchmarking utilities** — deterministic experiments, explicit objectives, and machine-readable results.
- **Reproducibility** — seeds, configuration, environment metadata, and experiment records are treated as first-class outputs.
- **Research archive** — selected results and findings from the predecessor research repositories are retained with provenance and limitations.

## Architecture

```
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
  +--> Other strategies
  |
  v
Validation & Benchmarking
  |
  v
Results + Metadata
```

## Status

The public repository is a clean consolidation of three research predecessors:

- `adaptive-topological-optimization`
- `bloc-reloc-v2`
- `cov-ia`

Only components that contribute to the framework's long-term utility are being migrated. Historical experiments remain explicitly identified as historical evidence rather than being presented as the current canonical implementation.

## Quick start

```bash
python -m pip install -e ".[dev]"
pytest
python examples/basic_usage.py
```

## Research principles

ATOF separates:

1. **method** — what the algorithm does;
2. **measurement** — how performance is evaluated;
3. **evidence** — which experiment produced the result;
4. **interpretation** — what the result may mean.

This prevents exploratory results, implementation history, and formal validation from being silently mixed.

## Limitations

ATOF is an active research project. Regime-aware selection is not assumed to be universally optimal, and historical benchmark results are not automatically treated as validation of the cleaned implementation. Every reported result should be read together with its benchmark protocol, data scope, seeds, and implementation version.

## Citation

See [CITATION.cff](CITATION.cff).

## License

MIT. See [LICENSE](LICENSE).
