# Fresh SOTA + adaptive-routing benchmark

This gate is the next experimental step after integrating KaMinPar and Mt-KaHyPar into the public ATOF portfolio.

## Candidate surface

The benchmark compares eleven strategies on the existing locked 20-graph k=2 corpus:

- BLOC-RELOC baseline
- BLOC-RELOC affinity
- BLOC-RELOC hybrid fixed
- BLOC-RELOC adaptive
- NetworkX Kernighan-Lin
- METIS
- KaHIP
- KaMinPar default
- KaMinPar strong
- Mt-KaHyPar default
- Mt-KaHyPar quality

Three seeds are fixed: 42, 101, and 2024.

## Isolation

METIS, KaHIP, KaMinPar, and Mt-KaHyPar execute in dedicated worker processes, so a native extension crash becomes an explicit benchmark error rather than terminating the entire comparison process.

The CI gate refuses to accept a scientific result when any graph/strategy/seed row is incomplete or errored.

## Measurements

Every row records:

- graph identity and topology size;
- corpus;
- seed;
- strategy;
- endpoint edge cut;
- exact balance error;
- wall-clock runtime;
- strategy-specific metadata when available.

The benchmark also persists the RegimeSignatureV2 topology descriptor alongside each graph.

## Routing transfer

After the 11-strategy benchmark, the second stage performs leave-one-corpus-out routing:

- nearest-neighbor topology router;
- centroid topology router;
- fixed majority strategy control;
- fixed global-mean strategy control.

The held-out corpus is excluded from router fitting and feature scaling.

The analysis reports graph-level relative regret and graph-normalized runtime ratio.

## Evidence boundary

This gate is not a claim that ATOF beats any individual solver. Its purpose is to establish the current external baseline surface and test whether topology-only routing transfers across graph families before adding trajectory-aware decisions.

The next research layer after this gate is the online controller: bounded probes, trajectory state, and compute allocation among the mature external solvers.
