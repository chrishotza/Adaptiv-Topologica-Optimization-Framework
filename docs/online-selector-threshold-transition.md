# Online selector threshold transition

PR #101 showed two stable threshold regimes on the same frozen selector:
0/0.25/0.5% produced identical activation and performance, while 1/2% produced
a materially lower probe rate and a much smaller selector improvement.

This follow-up does not tune or promote a threshold. It localizes the transition
with a fixed 0.5%–2.0% diagnostic grid and records both:

1. the training-only predicted relative deltas that drive the probe decision;
2. the held-out performance at each fixed threshold.

No threshold is selected automatically and no production/default behavior changes.
