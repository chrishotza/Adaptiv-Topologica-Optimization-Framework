# Reproducibility

Every reported result should identify:

1. implementation commit;
2. graph data and source;
3. objective and constraints;
4. random seeds;
5. software environment.

Recommended metadata:

```text
commit
dataset
graph
k
variant
seed
iterations
objective
balance_tolerance
runtime
result
```

Historical predecessor experiments used different objectives, graph suites, seeds, and implementations. They are therefore labeled historical and are not silently treated as benchmarks of the cleaned public implementation.

## Local reproduction

```bash
python -m pip install -e ".[dev]"
pytest
python examples/basic_usage.py
```
