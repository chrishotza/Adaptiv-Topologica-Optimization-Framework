# Online selector local predictor research

PR #103 showed that the frozen global pair-median predictor can assign the
same negative prediction to two held-out graphs with opposite outcomes.

This study compares that global predictor with a topology-local predictor.
For each held-out graph, candidate deltas are estimated from the k nearest
training graphs that exhibited the same ordered (rank-1, candidate) pair.
The topology distance uses the frozen router feature scaling and metric.

Fixed diagnostics:
- k in {3,5,7}
- trigger threshold in {0,0.5%,0.8%,0.9%}

The experiment is diagnostic only. No cell is selected automatically and
no production/default behavior changes.
