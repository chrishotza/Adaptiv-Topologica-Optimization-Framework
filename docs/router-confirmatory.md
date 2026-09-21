# Router confirmatory candidate comparison

The previous scaling ablation identified two candidate behaviors.

This follow-up freezes three configurations before execution:

1. all features + IQR + L2;
2. global-path features + IQR + L2;
3. global-path features + minmax + L2.

The experiment uses the same 17-graph leave-one-corpus-out protocol and retains the majority control. No new feature, scaler, or metric choice is selected during the confirmatory run.
