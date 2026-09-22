# Open-source access benchmark

## Purpose

ATOF does not need to claim universal algorithmic superiority to create user value.

The hypothesis under test is narrower and measurable:

> ATOF can provide a low-friction, zero-cost, reproducible entry point to graph partitioning workflows that would otherwise require choosing, installing, learning, and integrating several specialized tools.

This document defines how that hypothesis will be tested without turning "open source" into an unsupported marketing claim.

## What counts as evidence

The benchmark will report raw measurements rather than a single subjective score.

### Access surface

For each tool, record:

- license and acquisition cost;
- installation commands required;
- whether a compiler or native build is required;
- whether an MPI/runtime component is required;
- number of distinct setup stages;
- first successful import/API call;
- first successful partition from a common graph;
- supported input formats;
- machine-readable output options;
- deterministic seed/reproducibility controls;
- Python/API availability;
- documentation path to the first working result.

The benchmark must distinguish:

1. **zero-cost software** from
2. **zero-friction software**.

Open-source licensing proves the first. The measurements below test the second.

## Capability comparison

The first comparison surface is intentionally modest:

- ATOF product API / CLI;
- NetworkX Kernighan-Lin as a Python-native baseline;
- METIS;
- KaHIP.

The goal is not to declare a winner. It is to make the trade-offs visible.

For each common graph and k=2 partition:

- run the available method;
- record edge cut;
- record balance;
- record wall-clock time;
- record setup time separately from run time;
- preserve version/commit provenance.

The benchmark must not mix installation effort into algorithm runtime.

## ATOF-specific access claim

ATOF's access claim is satisfied only when a clean environment can go from installation to a reproducible result using a short documented path.

Target path:

```text
pip install -e .
        |
        v
import atof
        |
        v
optimize_graph(graph, k=2, seed=42, iterations=25)
        |
        v
machine-readable result
```

The current public CLI additionally supports:

```text
atof profile graph
atof optimize graph --output result.json
```

and the product loader accepts edge-list, GraphML, GEXF, and GML inputs.

## Commercially relevant interpretation

The relevant output is not "ATOF beats METIS."

The useful claim, when supported by measured data, is:

> A user can adopt ATOF at zero software license cost and with lower integration friction while still accessing a serious graph-partitioning workflow and public reproducibility evidence.

That is an adoption advantage, not an algorithmic superiority claim.

## Guardrails

This benchmark must not:

- compare unlike objectives without labeling them;
- compare optimized native binaries with unoptimized development installs and call the result an algorithmic comparison;
- convert setup complexity into a fabricated numerical score;
- claim universal superiority from the current corpus;
- hide cases where a competing tool is faster or produces a better partition;
- treat "open source" as evidence of quality by itself.

## Success condition

The access hypothesis is considered supported only if the published measurements show a consistent reduction in setup/integration friction for ATOF while the capability and quality comparison remains competitive on the common benchmark surface.

A result where ATOF is easier to adopt but occasionally slower or higher-cut is still a valid outcome. The product proposition is access and utility, not "win every graph."

## Next experiment

The next implementation step is a clean-environment benchmark that automatically records:

1. setup commands and successful completion;
2. first import/API success;
3. first partition success;
4. runtime on the common corpus;
5. edge-cut/balance results;
6. provenance.

The benchmark should run in GitHub Actions and publish raw JSON plus a human-readable summary.
