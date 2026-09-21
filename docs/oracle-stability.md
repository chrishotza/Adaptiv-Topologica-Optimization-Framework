# Oracle stability analysis

The routing experiments treat the lowest-mean edge-cut strategy on each graph as the graph-level oracle. Before interpreting router transfer failures, we need to know whether those labels are themselves stable.

The reproducible study is:

~~~bash
python -m experiments.run_oracle_stability
~~~

It reuses the same seven candidate strategies, three seeds, k=2 objective, and the same development/external/SNAP corpus loader used by the cross-corpus transfer study.

For each graph it records:

- per-seed edge cuts for every candidate strategy;
- the mean edge cut used to define the graph-level oracle;
- the gap between the oracle and runner-up;
- the fraction of seeds on which the graph-level oracle also wins;
- the distribution of oracle strategies across the corpus.

This separates two questions that were previously mixed together:

1. **Target stability:** is the oracle label reproducible across the configured seeds?
2. **Transfer:** can a router infer that label on an unseen corpus?

A low seed-consensus rate or a very small oracle margin means that some routing errors may be caused by an ambiguous target rather than by the topology representation.

A highly concentrated oracle distribution is a different issue: a router can obtain high agreement without learning a topology-conditioned policy if one fixed strategy dominates the corpus. The analysis therefore reports oracle diversity separately.

This is a diagnostic study, not a router-selection benchmark. It should be read together with the leave-one-corpus-out transfer results.


## Latest result

GitHub Actions run **35580179658** completed successfully on commit **5c236f2b855b842519c5bc90d9ec5aac505362ea**.

The 17-graph corpus produced stable graph-level oracle labels across the three configured seeds:

| Corpus | Graphs | Oracle diversity | Mean seed consensus | Graphs winning all seeds | Mean relative oracle margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 7 | 2 strategies | 1.0000 | 7/7 | 0.2331 |
| External | 4 | 3 strategies | 0.8333 | 2/4 | 0.0260 |
| SNAP | 6 | 1 strategy | 1.0000 | 6/6 | 0.4991 |

The development oracle distribution is Kernighan-Lin on five graphs and spectral bisection on two. External contains BLOC-RELOC baseline, Kernighan-Lin, and spectral bisection. All six SNAP graph-level oracles are Kernighan-Lin.

The main stability caveat is therefore not seed instability. The external corpus contains ties or near-ties on several graphs: its median oracle-relative margin is **0.0**, and only two of four graphs have the mean oracle winning all three individual seeds.

Overall, the configured oracle is reproducible enough to serve as the current routing target, while target diversity remains concentrated—especially in SNAP.