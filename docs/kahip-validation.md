# KaHIP strategy validation

This experiment adds KaHIP/KaFFPa as an independent partitioning family after the METIS validation. The purpose is **oracle diversification only**: KaHIP is not inserted into the routing model yet.

KaHIP v3.25 is available as a Python package on PyPI and documents pip installation plus the KaFFPa Python interface. The Strong preconfiguration is used here because the goal is a strong objective-aligned candidate rather than a lightweight baseline. citeturn219828view0turn652548view0

ATOF requires exact two-way balance. KaFFPa is therefore run with its documented 3% imbalance tolerance and any residual size imbalance is repaired deterministically by moving vertices with the smallest immediate cut increase until the exact ATOF floor/ceil split is reached.

The repaired edge cut is the benchmark metric.

## Candidate space

The baseline contains the eight strategies already validated through the METIS experiment, and adds:

- `kahip_kaffpa_strong_balanced`

The experiment does **not** change the topology features, router, scaling choices, seeds, or transfer protocol.

## Run

~~~bash
python -m experiments.run_kahip_validation
~~~

The output is `results/generalization/kahip_validation.json`.

## Interpretation

The result determines whether KaHIP contributes additional graph-level oracle winners beyond the current METIS-expanded strategy space.

- If KaHIP creates meaningful additional oracle diversity, the next transfer experiment can expand the candidate set from eight to nine strategies.
- If KaHIP rarely wins and the oracle remains concentrated, it should remain a diagnostic baseline rather than entering the router.

No public/default router change is made by this validation.
