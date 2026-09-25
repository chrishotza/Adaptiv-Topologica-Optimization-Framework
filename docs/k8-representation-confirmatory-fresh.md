# k=8 fresh representation confirmatory gate

This gate tests the frozen degree/hub representation against the original all-feature representation using entirely new solver outcomes.

Frozen:
- k=8
- same 20-graph corpus
- same 8 candidate strategies
- five new solver seeds: 1337, 2718, 3141, 1618, 65537
- leave-one-corpus-out training
- IQR scaling
- L2 distance
- graph-level mean relative regret

The graph corpus is deliberately unchanged. This is a fresh-outcome confirmation gate, not an external graph-domain validation.

The feature comparison is frozen before the new solver outcomes are generated. No production/default behavior changes.
