# k=8 fresh representation confirmation — negative result

This gate tested the frozen degree/hub representation against the original all-feature representation using five solver outcomes generated with a previously unused seed grid.

Frozen protocol:
- k=8
- same 20-graph corpus
- same 8 candidate strategies
- solver seeds: 1337, 2718, 3141, 1618, 65537
- leave-one-corpus-out training
- IQR scaling
- L2 distance
- graph-level mean relative regret
- paired bootstrap uncertainty
- majority control

## Result

The fresh solver outcomes do **not** confirm the earlier degree/hub advantage.

| Router | Mean relative regret |
|---|---:|
| all-features IQR/L2 | 12.9401% |
| degree/hub IQR/L2 | 91.2128% |
| majority control | 3.3350% |

Paired degree/hub minus all-features difference:
- mean: **+78.2727 percentage points**
- bootstrap 95% CI: **[-10.3760, +188.1935] pp**
- degree/hub better on 4 graphs
- degree/hub worse on 6 graphs
- ties on 10 graphs

The largest failures occur on development graphs, where the degree/hub representation can select poor strategies on the fresh solver outcomes. The result is therefore recorded as a **negative/inconclusive representation result**.

This does not invalidate the earlier prospective degree/hub replication on its original five-seed outcome set. It does show that the observed advantage is not stable across this fresh solver seed grid.

## Evidence boundary

The graph corpus is intentionally unchanged, so this is fresh solver-outcome confirmation rather than external graph-domain validation. The representation comparison was frozen before generating the outcomes. The held-out oracle was used only for evaluation. No production/default behavior was changed.

Artifact digest:
`sha256:00cfcfdf38425949e8771863c7cad5bb1a98b9b3f8849796707350598e255ea5`
