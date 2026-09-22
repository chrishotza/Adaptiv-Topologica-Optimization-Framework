# ATOF: AI-first agent guide

ATOF is an open-source graph optimization framework optimized for machine comprehension, low token overhead, reproducibility, and explicit evidence.

## First 30 seconds

1. Run "atof ai" for the stable machine contract.
2. Run "atof doctor" to inspect available backends and the execution environment.
3. Run "atof solve <graph>" for the shortest practical portfolio path.
4. Use "--compact" when topology detail or node assignments are not required.
5. Preserve "--seed" in reproducible experiments.
6. Use full JSON when evidence, provenance, or the partition mapping is required.

## Canonical commands

~~~bash
atof ai
atof doctor
atof solve graph.edgelist
atof solve graph.edgelist --partition-output partition.csv
atof profile graph.edgelist --compact
atof optimize graph.edgelist --engine portfolio --compact
atof optimize graph.edgelist --engine portfolio --output result.json
~~~

## Contract

- Default machine output is JSON.
- atof.ai.v1 describes capabilities and limits.
- atof.doctor.v1 describes backend availability.
- Portfolio mode is empirical selection under the current k=2 unweighted edge-cut contract.
- Optional backend failures are reported rather than silently hidden.
- Full results include provenance suitable for agent-to-agent handoff.

## Claim discipline

Do not claim universal optimality, universal speed superiority, or universal ease-of-use against every competing system. State the benchmark, corpus, objective, and environment when making comparative claims.
