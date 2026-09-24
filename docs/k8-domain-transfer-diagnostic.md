# k=8 domain-transfer diagnostic

This diagnostic reuses the frozen k=8 benchmark outcomes and compares two training regimes:

- cross-corpus leave-one-corpus-out, which is the primary benchmark;
- within-corpus leave-one-graph-out, used only as a domain-local transfer diagnostic.

Current observed evidence from the frozen benchmark:

- cross-corpus centroid regret: 19.51%;
- within-corpus centroid regret: 4.52%;
- within-corpus centroid regret on development: 0.93%;
- external: 17.11%; snap: 1.74%; snap_scalability: 1.66%.

The large reduction for development indicates that its cross-corpus failure is strongly associated with domain shift. This does not invalidate the primary cross-corpus result and is not used to replace it.