# KaHIP router confirmatory transfer

This experiment adds the independently validated KaHIP candidate to the locked METIS-expanded router protocol.

Candidate space:
- the seven original strategies;
- METIS (metis_multilevel_balanced);
- KaHIP (kahip_kaffpa_strong_balanced).

The three locked configurations are unchanged:
- all features + IQR + L2;
- global paths + IQR + L2;
- global paths + min-max + L2.

The corpus remains 17 graphs, with seeds 42, 101, 2024, k=2, and 25 refinement iterations.

The analysis is true leave-one-corpus-out transfer. Majority and per-corpus oracle distributions remain mandatory controls.

This experiment is confirmatory only. It does not change the public/default router.
