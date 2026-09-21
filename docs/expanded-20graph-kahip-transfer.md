# Expanded 20-graph KaHIP transfer

This experiment expands the validated nine-strategy leave-one-corpus-out protocol from 17 to 20 graphs by activating the repository's existing SNAP scalability corpus as a fourth held-out corpus.

Added graphs:
- ca-GrQc
- ca-HepTh
- wiki-Vote

The existing three locked routing configurations, k=2, seeds 42/101/2024, and 25 BLOC-RELOC refinement iterations remain unchanged.

The candidate strategy set remains exactly nine:
- the original seven strategies;
- METIS;
- KaHIP.

The fourth corpus is held out as a complete fold. No graph from the held-out corpus contributes to router fitting, scaling, or majority-label training for that fold.

This is a corpus-expansion validation experiment. It does not change the public/default router.
