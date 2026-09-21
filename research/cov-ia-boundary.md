# COV-IA boundary

COV-IA is a useful predecessor because it explored adaptive control driven by a dynamic state rather than a static configuration.

It is **not** merged into the ATOF optimization core.

The predecessor simulated:

- model-size choices;
- numerical precision choices;
- synthetic latency;
- synthetic accuracy;
- synthetic cost;
- dynamic load;
- a separatrix-based state signal.

That makes it useful as a conceptual parallel for adaptive decision systems, but not as graph-partitioning evidence.

The public ATOF design therefore keeps the conceptual lesson — **observe state, classify regime, select action, measure outcome** — while avoiding unrelated code and avoiding promotion of synthetic inference numbers as empirical serving measurements.

A future integration should happen only if a generic adaptive-control interface emerges that is useful to both domains without weakening either one.
