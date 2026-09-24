# Oracle-free online selection from the topology-ranked candidate set

The top-k coverage experiment established that the frozen topology router places the per-seed oracle inside the top-2 and top-3 candidate sets at measurable rates, while best-of-k remains a hindsight ceiling.

This experiment tests the narrower operational question: can one use only training-fold outcomes to decide whether to spend one additional full solver run, and which alternate to probe?

For each leave-one-corpus-out fold:

- the topology router is fitted exactly as in the top-k coverage protocol;
- each training graph/seed contributes relative edge-cut deltas for rank-2 and rank-3 candidates against rank-1;
- the selector estimates a median delta, conditioned on the ordered rank-1/rank-j strategy pair, with candidate and rank fallbacks;
- a held-out graph first runs rank-1;
- exactly one alternate is probed only when the training-only prediction is strictly improving;
- after the probe, the lower observed edge cut is retained.

The probe decision never reads held-out oracle labels. The evaluation still reports best-of-2 and best-of-3 hindsight ceilings as context, but those are not deployable policies.

No production/default behavior changes.
