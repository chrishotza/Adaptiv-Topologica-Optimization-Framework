# Router confirmatory candidate comparison

The previous scaling ablation identified two candidate behaviors.

This follow-up freezes three configurations before execution:

1. all features + IQR + L2;
2. global-path features + IQR + L2;
3. global-path features + minmax + L2.

The experiment uses the same 17-graph leave-one-corpus-out protocol and retains the majority control. No new feature, scaler, or metric choice is selected during the confirmatory run.


## Latest result

GitHub Actions run **35580437557** completed successfully on commit **0b0c57fc556c08cad840970438cf92dec54b354f**.

All three configurations were evaluated on the same 17-graph leave-one-corpus-out protocol with three seeds and 25 refinement iterations.

| Configuration | Centroid regret | 1-NN regret | Majority regret | Centroid agreement | 1-NN agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| all + IQR + L2 | 0.6408 | 0.6002 | 0.3242 | 0.5476 | 0.4127 |
| global paths + IQR + L2 | **0.4673** | 0.6232 | 0.3242 | 0.5397 | 0.4127 |
| global paths + minmax + L2 | 0.5649 | **0.5843** | 0.3242 | 0.4841 | 0.4603 |

The confirmatory comparison therefore reproduces a meaningful effect of representation/scaling on topology-conditioned routing, but **none of the three learned configurations beats the majority control** on mean relative regret.

The most competitive locked configuration for the centroid router is global-path + IQR + L2. For 1-NN, global-path + minmax + L2 is the strongest of the three locked candidates. These are descriptive results, not a reason to change the public default router.

Together with oracle stability, the evidence points to the current bottleneck being **strategy-space/oracle diversity rather than random seed instability**. Further feature tuning is not justified by this confirmatory phase alone.