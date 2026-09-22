# ATOF: AI-first agent guide

ATOF is an open-source graph optimization framework. Optimize for **fast machine comprehension, low token usage, reproducibility, and explicit evidence**.

## First 30 seconds

1. Read the command "atof ai" for the current machine contract.
2. Prefer "atof optimize <graph> --engine portfolio --compact" for a practical result.
3. Use "atof profile <graph> --compact" when only topology/regime context is needed.
4. Use "--seed" for reproducibility.
5. Inspect full JSON only when topology or the node-to-block mapping is required.

## Canonical commands

~~~bash
atof ai
atof profile graph.edgelist --compact
atof optimize graph.edgelist --engine portfolio --compact
atof optimize graph.edgelist --engine portfolio --output result.json
~~~

## Output contract

Default CLI output is JSON. Compact output intentionally omits verbose topology and node-to-block mappings. Portfolio output reports backend availability and errors instead of hiding optional dependency failures.

## Product semantics

- portfolio: run available backends under a common k=2 balanced edge-cut contract and select the lowest observed edge cut.
- bloc: use the public BLOC-RELOC product path.
- Routing/regime labels are descriptive heuristics, not universal guarantees.
- The repository separates method, measurement, evidence, and interpretation.

## Do not overclaim

Do not describe ATOF as universally optimal or as universally faster/better than METIS, KaHIP, or NetworkX. The open-source value proposition is **one accessible interface, comparable outputs, reproducibility, and optional backend composition**.
