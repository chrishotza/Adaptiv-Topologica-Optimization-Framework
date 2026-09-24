# k=8 degree/hub prospective replication

The frozen k=8 all-feature benchmark showed a strong post-hoc feature-ablation signal: the five degree/hub features reduced cross-corpus routing regret from 19.51% to 1.30% on the same solver outcomes.

This experiment freezes that feature subset before a new solver run and evaluates it on the same 20-graph corpus with five seeds: 7, 42, 101, 2024, 8191.

The result is a seed replication of the candidate routing configuration. It does not replace the original all-feature k=8 endpoint and makes no production/default change.
