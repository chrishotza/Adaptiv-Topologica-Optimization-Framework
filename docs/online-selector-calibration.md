# Online selector calibration

PR #102 localized the trigger transition to the interval between 0.8% and 0.9%.
This study addresses the next evidence question: whether the training-only
predicted alternate benefit corresponds to realized held-out benefit.

The analysis is diagnostic only. It records:
- prediction error against the realized held-out alternate-vs-top1 delta;
- sign agreement and correlation;
- fixed prediction-magnitude bins;
- fixed activation diagnostics at 0.5%, 0.8%, 0.9%, and 1.0%;
- per-graph, per-seed outcomes for auditability.

No threshold is selected automatically and no production/default behavior changes.
