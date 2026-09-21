# Dynamics observatory

ATOF preserves the per-iteration trace produced by optimization strategies so that search behavior can be studied separately from final solution quality.

## Trace model

The current BLOC-RELOC trace records:

- iteration;
- weighted objective;
- unweighted edge cut;
- accepted moves;
- rejected moves.

This is enough to measure search activity without changing the optimization objective.

## Canonical descriptive metrics

\`atof.dynamics.summarize_trace()\` reports:

- **weighted improvement** — initial weighted cost minus final weighted cost;
- **relative improvement** — weighted improvement divided by initial cost;
- **total accepted / rejected** — accumulated search decisions;
- **acceptance rate** — accepted decisions divided by all decisions;
- **active iterations** — iterations with at least one accepted move;
- **extinction iteration** — the last active iteration, expressed with one-based indexing;
- **trailing inactive iterations** — consecutive inactive iterations at the end;
- **maximum accepted moves per iteration** — peak local activity.

These are descriptive measurements. They do not by themselves establish causality, superiority, or a mechanism.

## Historical observatory mapping

The predecessor \`bloc-reloc-v2\` used a broader Dynamics Observatory with metrics such as survival, extinction, avalanche activity, correlations, and mechanism fingerprints.

ATOF does not copy those labels blindly. The public framework first defines a minimal trace-derived metric layer whose semantics are directly recoverable from the current optimizer.

Additional survival or event-analysis modules should be introduced only when their operational definitions and statistical validity are explicit.

## Research use

A benchmark record should preserve:

1. the raw trace;
2. the final partition metrics;
3. the topology profile;
4. the strategy parameters;
5. the dynamics summary.

This makes it possible to ask whether different topological regimes produce systematically different search dynamics while keeping the optimization result and the measurement protocol separate.
