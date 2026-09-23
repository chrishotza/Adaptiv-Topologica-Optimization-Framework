# Regime / trajectory v2 research layer

This change adds a frozen-friendly research layer for topology-aware control without changing the default product solver.

## Regime Signature v2

Regime Signature v2 extends the existing topology profile with:

- degree coefficient of variation;
- hub concentration;
- connected-component count and giant-component fraction;
- edge/node ratio;
- logarithmic graph-size descriptors;
- explicit structural flags.

The signature is descriptive. The thresholds are configuration parameters and are not claimed to be universally validated.

## Trajectory State Monitor

The monitor consumes only the optimization-trace prefix available at the current decision point.

Signals include:

- stagnation length;
- recent gain;
- recent acceptance rate;
- gain decay;
- trailing inactivity;
- optional boundary pressure, hub exposure, and block-gain variance telemetry.

The monitor emits one operational state:

- active;
- stagnating;
- exploratory_excess;
- premature_collapse;
- extinct.

These are search-state signals, not causal labels.

## Portfolio Controller v2

The controller exposes four actions:

- continue;
- intensify;
- switch;
- stop.

A switch requires an observed bounded-probe improvement over the current strategy and sufficient remaining budget. The controller has no access to graph-level oracle labels.

## Counterfactual routing protocol

The leave-one-family-out protocol evaluates routing with a complete family held out at a time.

The protocol requires:

1. all graphs in the held-out family are excluded from fitting;
2. predictions are generated before reading held-out oracle performance;
3. held-out graph identity cannot appear in the training set;
4. family definitions are supplied explicitly by the benchmark.

This is intended as the next confirmatory gate for topology-to-strategy transfer.
