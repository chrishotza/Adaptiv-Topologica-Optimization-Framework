# SNAP empirical corpus

ATOF 0.5.0 adds a reproducible ingestion layer for public graph datasets from Stanford's SNAP collection.

## Routine corpus

The routine corpus contains four empirical datasets chosen to broaden the evidence surface while keeping live validation practical:

- **C. elegans frontal** — 131 nodes, 764 directed edges in the source.
- **Florida Bay** — 128 nodes, 2,106 directed edges in the source.
- **S. cerevisiae** — 690 nodes, 1,094 directed and signed edges in the source.
- **email-Eu-core** — 1,005 nodes, 25,571 directed edges in the source.

SNAP describes these datasets and their provenance on the official dataset pages:

- https://snap.stanford.edu/data/C-elegans-frontal.html
- https://snap.stanford.edu/data/Florida-bay.html
- https://snap.stanford.edu/data/S-cerevisiae.html
- https://snap.stanford.edu/data/email-Eu-core.html

The benchmark deliberately does not use node metadata, community labels, edge signs, or edge weights as predictive inputs.

## Normalization boundary

The current ATOF objective is **unweighted undirected partitioning**. Therefore the loader:

1. parses the public gzip edge list;
2. converts directed sources to undirected connectivity;
3. removes self-loops;
4. relabels nodes to a compact integer range.

This normalization is not a claim that direction or sign is unimportant in the original scientific datasets. It only defines the exact representation on which this version of ATOF is evaluated.

## Provenance

Third-party graph files are intentionally **not vendored** into the repository. The loader caches the compressed file locally and records:

- source URL;
- reference URL;
- file size;
- SHA-256 digest;
- declared and loaded graph sizes;
- source-directed flag;
- normalization rule.

This makes a result manifest self-describing without turning the Git repository into a data mirror.

## Scalability corpus

The separate scalability registry includes:

- **ca-GrQc** — 5,242 nodes, 14,496 edges;
- **ca-HepTh** — 9,877 nodes, 25,998 edges;
- **Wiki-Vote** — 7,115 nodes, 103,689 directed edges in the source.

These are deliberately not part of the routine validation job. They are a separate tier because larger graphs change runtime and stress the topology profiler and optimizer in ways that should be measured explicitly.

## Run

~~~bash
python -m experiments.run_snap_validation
~~~

Results are written to:

~~~text
results/snap/latest.json
~~~

GitHub Actions also exposes a manual live-data workflow named `SNAP validation` so the corpus can be re-run against the current public source files without making every pull request depend on third-party network availability.

## Interpretation

Adding this corpus does not by itself establish broad generalization. The routine corpus is still small and domain-specific, and the current objective deliberately discards source direction/sign semantics.

The purpose of 0.5 is to create a clean bridge from synthetic development graphs and tiny built-in empirical references toward a traceable, externally sourced validation surface.

## Expanded routine corpus

The routine empirical tier now contains two additional moderate-size SNAP graphs: **CollegeMsg** (1,899 nodes; 20,296 static edges after source temporal normalization) and **reachability** (456 nodes; 71,959 source edges). Both are retained as directed-source metadata and normalized to the current simple undirected connectivity objective.