# k=8 external runtime preflight

This is a timing/feasibility probe only.

Frozen scope:
- one external graph: ego-Facebook
- one seed: 5003
- k=8
- 25 iterations
- full `optimize_portfolio(include_optional=True)`
- timing for all-feature, global-path, and degree/hub topology profiling

The probe does not evaluate routing quality and does not replace the external holdout.

The result is used to establish:
1. graph loading cost;
2. topology profiling cost by feature family;
3. total solver cost;
4. per-backend runtime;
5. a safe partitioning/checkpoint plan for the later external holdout.
