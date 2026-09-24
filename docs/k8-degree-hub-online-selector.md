# k=8 degree/hub online selector

This experiment transfers the validated oracle-free selector protocol from k=4 to k=8 after the degree/hub routing configuration was prospectively replicated.

The selector:
- ranks candidates with the frozen degree/hub IQR/L2 router;
- predicts rank-2/rank-3 alternate deltas using training-only ordered-pair medians;
- probes one alternate only when predicted delta is negative;
- evaluates held-out outcomes only after the decision.

The budget-matched random control receives exactly the same number of probe graphs in each held-out corpus and repeats allocation 500 times.

No production/default behavior changes.
