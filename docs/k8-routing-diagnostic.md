# k=8 routing diagnostic

This diagnostic preserves the frozen k=8 benchmark as the primary endpoint and adds reproducible sensitivity views.

Purpose:
- global centroid and majority regret;
- per-corpus regret;
- leave-one-corpus-out sensitivity;
- the five largest centroid-regret graphs.

These views are diagnostic only. They do not replace the primary 20-graph endpoint.

Current k=8 evidence:
- global centroid regret: 19.51%;
- majority regret: 3.35%;
- the development fold is 53.93% centroid regret;
- excluding the entire development corpus leaves 0.97% centroid regret across the remaining 13 graphs;
- the two largest outliers are development/stochastic_block at 142.6% and development/watts_strogatz at 226.3%.

This is a domain-shift sensitivity finding, not a revised benchmark result.