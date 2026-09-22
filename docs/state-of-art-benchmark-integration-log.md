# State-of-art benchmark integration log — 2026-09-22

## Run 26

GitHub Actions workflow: `State-of-art benchmark #26`.

Commit tested: `63a919e07a92e6caf6846063071ecd693288acf1` and its immediately preceding benchmark revisions.

The workflow completed successfully and produced the 20-graph benchmark artifact. The artifact contained 660 graph/seed/strategy rows across 20 graphs and 11 candidate strategies.

Environment recorded by the benchmark:

- ATOF 0.6.0
- NetworkX 3.7
- PyMetis 2025.2.2
- KaHIP 3.25
- KaMinPar 3.7.3
- Mt-KaHyPar 1.6.2

## Integration failures found

The first execution exposed three adapter bugs:

1. METIS and KaHIP helper functions use keyword-only `seed`, while the generic runner initially supplied it positionally.
2. The KaMinPar Python binding constructor is `KaMinPar(num_threads, ctx)`, not the keyword form used by the first adapter revision.
3. Those failures were recorded explicitly in the benchmark instead of being silently excluded.

## Scientific status

This run is **not used as a scientific comparison result** because the candidate set was incomplete: METIS, KaHIP, and most KaMinPar rows failed integration in that execution.

Mt-KaHyPar default and quality did execute successfully across the corpus, confirming the current Python package is installable in the GitHub Actions environment and that its adapter can produce graph-level rows under the ATOF contract.

The adapter corrections are now committed on the research branch. A subsequent benchmark execution is required before any cross-solver quality/runtime conclusions are published.

## Reproducibility

The raw artifact is retained by GitHub Actions. The corrected benchmark should be treated as the first valid scientific run once all required strategies complete successfully on the same corpus.