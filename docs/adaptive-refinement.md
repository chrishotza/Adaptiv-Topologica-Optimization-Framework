# Adaptive refinement controller

ATOF now supports a state-aware refinement policy for the native BLOC-RELOC Engine.

## Design principle

The expensive two-node swap neighborhood should not be scheduled only by a fixed clock. The controller observes the objective gain of each local-relocation iteration and treats repeated low-gain iterations as a stagnation signal. In adaptive mode, a cheap sampled-swap probe is then used as a witness: the full hybrid pass is paid only when the probe finds an improving swap.

With `--hybrid-policy adaptive`, ATOF:

1. runs the normal relocation neighborhood;
2. measures the local objective gain;
3. counts consecutive low-gain iterations;
4. calibrates the hybrid neighborhood with the first scheduled full pass;
5. repeats the full pass while it remains productive;
6. after an unproductive pass, uses the hybrid period as a minimum cooldown between adaptive probes and resumes full passes only when a probe finds an improving move.

The rule is deterministic for a fixed graph, seed, and configuration. It does not require a trained model.

## Why this direction matters

Recent graph-partitioning work continues to derive gains by combining multilevel structure, local refinement, and better decisions about where computation should be spent. The adaptive controller is deliberately narrower: it turns the search trajectory itself into a control signal, so the expensive neighborhood is invoked because the solver is stalling rather than because an iteration number was reached.

## Product interface

Fixed schedule remains available:

```bash
atof optimize graph.edgelist --engine bloc --hybrid --hybrid-policy fixed
```

State-aware schedule:

```bash
atof optimize graph.edgelist --engine bloc --hybrid --hybrid-policy adaptive --hybrid-patience 2
```

The machine-readable `atof.optimize.v1` result declares the policy, period, patience, probe size, probe count, and number of full hybrid passes.

## Research protocol

The repository benchmark compares fixed and adaptive policies over the same synthetic suite, seeds, variants, iteration budget, and two-swap sample budget. The primary questions are whether adaptive refinement preserves edge-cut quality and whether it reduces the number of expensive hybrid passes and total runtime.

No claim of state-of-the-art superiority is made until the adaptive policy is validated beyond the existing synthetic suite.
