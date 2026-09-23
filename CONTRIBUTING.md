# Contributing to ATOF

ATOF is an open-source graph optimization project. Contributions are welcome in product engineering, backend integrations, reproducible benchmarking, research experiments, documentation, and AI-agent tooling.

## Core principle

Every meaningful advance should become one of:

1. a usable product capability;
2. a reproducible benchmark or research instrument;
3. a clearer machine-readable contract.

Do not turn a benchmark result into a product claim without a documented promotion step.

## Development

Install the development environment:

```bash
python -m pip install -e ".[dev]"
pytest
```

Optional solver stacks:

```bash
python -m pip install -e ".[metis,kahip,kaminpar,mtkahypar]"
```

Run the product surface:

```bash
atof ai
atof doctor
atof solve examples/demo.edgelist
atof optimize examples/demo.edgelist --engine portfolio --k 4 --compact
```

## Backend contributions

New backends should:

- use the common graph contract;
- report edge cut, balance error, runtime, and backend version;
- preserve deterministic seed handling where the upstream backend supports it;
- distinguish dependency absence from execution failure;
- avoid silently changing the public default;
- include focused tests for availability, result validation, and failure behavior.

Native C/C++ extensions that can terminate the interpreter should run through the repository's isolation pattern when used by research benchmarks or the product portfolio.

## Benchmark contributions

A benchmark PR should record:

- corpus and graph identifiers;
- objective and balance contract;
- seeds;
- iteration/time budgets;
- package versions;
- CPU/thread environment when relevant;
- graph hashes or upstream provenance;
- exact command or workflow used;
- whether timings include graph/backend initialization.

Comparative results must remain corpus- and protocol-specific. Do not describe one benchmark as universal superiority.

## State-of-the-art research

The current research map is maintained in `docs/state-of-art-2026-map.md`.

The main open research tracks are:

- mature multilevel quality;
- learned internal heuristics;
- k-way and large-k partitioning;
- linear-time/scalability methods;
- multi-constraint graph partitioning;
- hypergraph and multi-objective extensions;
- dynamic compute allocation.

The dynamic allocation track currently includes a non-default marginal-return controller based on observed gain per structural-work unit. It is experimental until matched quality-vs-compute validation supports promotion.

## Pull requests

Keep product changes and research-only changes clearly separated in scope and documentation.

A strong PR includes:

- a concise statement of the change;
- tests;
- evidence of the relevant benchmark or contract;
- explicit limitations;
- reproducibility instructions.

For state-of-art work, the benchmark protocol is part of the result. A faster script with an altered objective or balance contract is not a matched comparison.

## Licensing

ATOF is distributed under the MIT License. Do not add dependencies or copied source with incompatible licensing without documenting the issue first.
