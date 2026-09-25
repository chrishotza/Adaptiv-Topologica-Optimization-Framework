# k=8 hybrid representation confirmatory gate

## Exploratory basis

On the completed fresh-outcome representation comparison, the degree/hub-only representation failed badly on several regular development graphs, while adding the three global-path features to degree/hub reduced the same post-hoc regret substantially.

That retrospective observation is **not** confirmatory evidence. It is only the basis for freezing the following candidate before a new solver seed grid is generated:

- density
- avg_degree
- degree_std
- hub_ratio
- degree_gini
- core_number
- diameter
- avg_path_length

Scale: IQR. Distance: L2. Training: leave-one-corpus-out.

## Confirmatory protocol

- k=8
- same 20-graph corpus
- same 8 strategies
- five new solver seeds: 7001, 8192, 104729, 131071, 262144
- compare all-features, degree/hub-only, global-paths-only, and frozen hybrid
- majority control
- graph-level mean relative regret
- 5,000-resample bootstrap CIs
- no production/default changes

This is a fresh solver-outcome gate, not external graph-domain validation. The candidate feature set is frozen before these new outcomes are generated.
