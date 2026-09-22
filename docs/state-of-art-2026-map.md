# 2026 state-of-the-art map

This document records the external methods that materially define the current balanced graph-partitioning research surface relevant to ATOF.

## 1. Multilevel partitioning remains the reference architecture

KaMinPar, KaHIP, and METIS represent the core multilevel family used for high-quality balanced graph partitioning. METIS documents multilevel recursive bisection and multilevel k-way schemes; KaMinPar provides shared-memory and distributed-memory multilevel partitioning with explicit quality/speed contexts; KaHIP provides high-quality partitioning with strong refinement and additional variants.

- METIS: https://github.com/KarypisLab/METIS
- KaHIP: https://github.com/KaHIP/KaHIP
- KaMinPar: https://github.com/KaHIP/KaMinPar

## 2. KaMinPar currently exposes an unusually broad scalability surface

KaMinPar documents default, eco, strong, terapart, and large-k contexts and supports shared-memory and distributed-memory execution. Its current release line is 3.7.x; the 3.7.3 release is dated March 2026. The project also documents very large-scale examples and strict balance for unweighted input.

Research implication for ATOF: a comparison limited to a single KaMinPar setting is insufficient. Quality-oriented and speed-oriented contexts should be treated as distinct candidates.

## 3. Linear-time multilevel partitioning

Gottesbüren et al., ESA 2025, introduce a linear-time multilevel algorithm through edge sparsification while retaining multilevel refinement. Their KaMinPar integration reports 1.49x average speedup, up to 4x on some instances, with about 1% solution-quality loss in the reported evaluation.

https://doi.org/10.4230/LIPIcs.ESA.2025.32
https://arxiv.org/abs/2504.17615

Research implication for ATOF: runtime is not simply an implementation detail. Modern work explicitly changes the computational envelope of the multilevel hierarchy.

## 4. Memory-scale multilevel partitioning

Salwasser et al., Tera-Scale Multilevel Graph Partitioning, target the memory bottleneck of extreme-scale multilevel partitioning. The work reports large reductions in peak memory and demonstrates trillion-edge-scale partitioning on a single machine and much larger distributed settings.

https://arxiv.org/abs/2410.19119

Research implication for ATOF: the later benchmark phase must distinguish ordinary desktop-scale quality comparisons from memory/scalability comparisons. A 20-graph mixed corpus is not a proxy for tera-scale behavior.

## 5. Learned heuristics are now being inserted inside the multilevel solver

Schrape et al., SEA 2026, report a learned coarsening method integrated into Mt-KaHyPar. A pre-trained neural network predicts an edge score used to guide coarsening decisions. The paper evaluates more than 180 graphs, reports an average quality improvement of 2% on a class of graphs with beneficial properties, unchanged quality on the remaining graphs, and reports generalization to literature instances larger than the training graphs.

https://doi.org/10.4230/LIPIcs.SEA.2026.25
https://zenodo.org/records/19387774

The paper's training protocol uses repeated high-quality partitioning runs over multiple k values and then trains on one million sampled edges, with graph-balanced sampling. It also evaluates graph-level generalization using eight-fold cross-validation.

Research implication for ATOF: a high-level external router is not the only current ML direction. Stronger state-of-art work learns inside coarsening/refinement decisions while preserving the multilevel solver. Any ATOF novelty claim must be distinguished from this class of methods.

## 6. GPU multilevel partitioning

Jet is a GPU-oriented multilevel graph partitioning line reported in the SIAM Journal on Scientific Computing in 2024. It extends the modern multilevel design to accelerator-oriented execution.

https://doi.org/10.1137/23M1559129
https://arxiv.org/abs/2304.13194

Research implication for ATOF: a runtime claim should specify the hardware regime. CPU-only Python timing is not directly comparable to GPU multilevel throughput.

## 7. Learned and language-model approaches

Recent work also evaluates inductive and LLM-based approaches to graph partitioning. PR-GPT uses pretraining on smaller graphs, inductive inference, and refinement. A 2025 EMNLP paper studies whether LLMs can perform graph partitioning and uses a refinement stage to restore topological consistency.

https://arxiv.org/abs/2409.00670
https://aclanthology.org/2025.emnlp-main.792/

These approaches are adjacent to the ATOF research program but are not substitutes for a matched classical solver comparison.

## 8. What is distinctive about the ATOF hypothesis

The current ATOF hypothesis is not simply 'use ML to partition a graph'. The narrower research question is whether a controller can allocate expensive search budget dynamically among complementary neighborhoods or solver components using observed marginal return, while preserving quality through explicit safety gates.

That hypothesis should be tested against two competing families:

1. static strong solvers and multilevel configurations;
2. learned internal heuristics that change decisions within a solver.

A convincing result would therefore need a matched quality-vs-compute frontier, graph-level holdouts, reproducible seeds, and per-instance regression accounting.

## 9. Benchmark expansion required after the 20-graph gate

The repository's current 20-graph benchmark is a controlled first gate. The next external-data gate should incorporate the public SEA 2026 benchmark material, preserving training/test boundaries and provenance rather than copying training graphs into a routing corpus.

The goal is not to imitate the paper's exact experiment. The goal is to establish a common external corpus on which ATOF, KaMinPar, KaHIP, METIS, and future learned or adaptive controllers can be compared under explicitly matched contracts.

## 10. Decision gates

- Gate A: 20-graph, k=2 head-to-head benchmark.
- Gate B: verified KaMinPar default/strong integration.
- Gate C: k-way parity, at least k=4.
- Gate D: external benchmark expansion using a documented 2026-era corpus.
- Gate E: dynamic compute-allocation study against fixed strong baselines.
- Gate F: only then assess whether ATOF contributes a distinct improvement in the quality/runtime frontier.
## SEA 2026 benchmark dimensions that ATOF must match

The published SEA 2026 evaluation uses k in {4, 8, 32, 64}, epsilon=0.03, five randomized runs per graph/k combination, and a one-hour time limit. It reports arithmetic means over seeds and geometric means over benchmark instances.

The main Set A contains 118 graphs spanning 29k to 53M edges. The additional scale sets contain 38 irregular graphs (5.4M–1.8B edges) and 33 regular graphs (12M–575M edges), giving 189 instances across Set A, I, and R.

The learned coarsening method trains on 20 graphs in Set B1-20, which are a subset of Set B and therefore a small subset of Set A. The published generalization protocol uses eight-fold cross-validation over Set A.

The final reported Set A geometric means are 0.36 s and baseline-relative cut 0.00% for Mt-KaHyPar, 0.41 s and -0.34% for the learned coarsening approach, 0.38 s and +20.34% for Metis-K, and 0.68 s and +20.05% for Metis-R. The learned approach therefore trades about 14% runtime overhead for a small geometric-mean quality improvement over the unconstrained Mt-KaHyPar baseline in the published environment.

These numbers are not ATOF measurements and are not directly comparable to our Python timings. They are the numerical target defining the external research frontier we need to reproduce under a controlled contract.

The Zenodo record contains the public benchmark sets, training data, labels, and benchmark results. Its archive is very large, so ATOF should consume it selectively and record file hashes/provenance instead of vendoring the dataset.
## Current ATOF integration status

ATOF now has executable Python adapters for KaMinPar and Mt-KaHyPar. The k=2 benchmark includes KaMinPar default/strong plus Mt-KaHyPar default/quality; the k-way scaffold includes the same families for k=4, 8, 32, 64.

Mt-KaHyPar default/quality are current upstream multilevel presets. They must not be described as the SEA 2026 learned-coarsening model: the SEA contribution adds a pre-trained neural score to the coarsening stage inside Mt-KaHyPar. The paper reports 0.3–1.4% quality improvement over its Mt-KaHyPar baseline with 14% average runtime overhead in the published AVX2 implementation (DOI: https://doi.org/10.4230/LIPIcs.SEA.2026.25).

Zenodo provides the Set A/B benchmark files and a compact benchmark-results archive. Set A contains 118 unweighted METIS-format graphs, while the complete archived material totals 348.2 GB; the benchmark-results archive is only 2.5 MB (DOI: https://doi.org/10.5281/zenodo.19387774).
## GPU multilevel reference

Jet is a GPU-oriented multilevel graph partitioner whose refinement and coarsening are designed for accelerators. Its evaluation compares against shared-memory CPU partitioners on a broad graph set. G-kway is another GPU multilevel line reporting large speedups while maintaining comparable partition quality.

- Jet: https://doi.org/10.1137/23M1559129
- G-kway: https://doi.org/10.1145/3734522

These methods belong to a different hardware regime. ATOF's CPU benchmark must not mix their throughput numbers with CPU wall-clock measurements; the correct comparison is algorithmic quality at matched hardware or a separate hardware-specific track.

## 2026 second-half refresh

The state-of-the-art map was refreshed in September 2026 against the current literature.

### Multi-constraint graph partitioning: multilevel + tabu search

Lu, Chen, Gao, and Hao published a multilevel iterated tabu-search approach for multi-constraint graph partitioning in *Computers & Operations Research* (2026). Their method combines problem-specific multilevel coarsening with feasible/infeasible iterated tabu search and reports new upper bounds on 573 of 665 benchmark instances, matching 83 previous best-known bounds.

https://doi.org/10.1016/j.cor.2026.107389

This is an important algorithmic reference for ATOF's **future multi-constraint track**, but it is not a direct baseline for the current single-constraint, unweighted graph product. The transferable idea is architectural: multilevel reduction plus an adaptive refinement/search process can be more important than any single local move operator.

### Multi-objective hypergraph partitioning: multilevel continuous optimization

Li et al. published a 2026 multi-objective hypergraph partitioning framework combining minimum-spanning-tree structure with proximal-gradient optimization in a multilevel setting.

https://doi.org/10.1007/s11227-026-08738-5

This belongs to ATOF's **hypergraph/multi-objective frontier**, not its current graph edge-cut contract. It reinforces the need to keep objective semantics explicit: quality claims from multi-objective hypergraph methods cannot be compared directly with unweighted graph edge cut.

### Scope boundary for newly surfaced 2026 work

Recent September 2026 graph-partitioning papers also target semi-supervised image segmentation or domain-specific DAG partitioning. These are useful adjacent research signals, but they should not enter the core ATOF state-of-art benchmark unless the objective, graph model, and constraints match the product contract.

## 11. State-of-the-art coverage model for ATOF

The research program is organized around **coverage**, not a single leaderboard position.

| Frontier | What the external state of the art does | ATOF status |
|---|---|---|
| Mature multilevel quality | Mt-KaHyPar and KaMinPar combine coarsening, refinement, parallel engineering, and multiple quality/speed configurations | Product adapters + matched research benchmark |
| Learned internal heuristics | SEA 2026 inserts a pre-trained model into Mt-KaHyPar coarsening rather than replacing the solver with end-to-end ML | Exact software snapshot smoke-tested; matched multi-graph benchmark pending |
| Near-linear multilevel scaling | ESA 2025 integrates edge sparsification into KaMinPar to force geometric hierarchy shrinkage, reporting linear expected work with limited average quality loss | Not yet integrated; separate scalability track |
| Large-k / extreme scale | KaMinPar explicitly targets very large k and large shared/distributed-memory graphs | Current product accepts k-way requests; large-scale corpus track pending |
| Multi-constraint hypergraph partitioning | ESA 2026 improves rebalancing inside Mt-KaHyPar for multi-constraint hypergraph objectives | Adjacent capability; ATOF graph product remains unweighted/single-constraint |
| Dynamic compute allocation | The research opportunity is to decide what computation to spend next based on observed marginal return, rather than merely selecting one static solver | ATOF's distinctive experimental track |

### Coverage principle

ATOF does not need to reproduce every implementation detail of every frontier algorithm inside its own codebase. The useful target is to provide:

1. a common machine-readable contract;
2. reproducible access to major open-source solvers when available;
3. provenance and validation around every candidate result;
4. a benchmark layer that can reproduce important published protocols;
5. an adaptive orchestration layer that can decide where additional compute is worth spending.

This makes the product useful even when an external solver remains stronger on a particular graph family.

### Immediate frontier gates

- **G1 — Product parity:** expose mature open-source backends directly through the solve/portfolio product path.
- **G2 — k-way parity:** complete k={4,8,32,64} matched evaluation on the locked corpus.
- **G3 — SEA parity:** execute the exact 1.5.3 learned-coarsening snapshot on a matched subset of Set A.
- **G4 — Set A:** materialize the 118-graph evaluation surface with hashes and source provenance; manual gate now implemented.
- **G5 — Dynamic allocation:** evaluate quality-vs-structural-work curves against fixed strong baselines.
- **G6 — Scale track:** evaluate large Set I/R-style instances separately from desktop-scale quality experiments.

The external frontier therefore becomes a **living test surface** for ATOF rather than a fixed list of competitors.

### External references

- SEA 2026 learned coarsening: https://doi.org/10.4230/LIPIcs.SEA.2026.25
- SEA 2026 Mt-KaHyPar artifact 1.5.3: https://doi.org/10.4230/artifacts.26212
- ESA 2025 linear-time multilevel partitioning: https://doi.org/10.4230/LIPIcs.ESA.2025.32
- KaMinPar artifact: https://doi.org/10.4230/artifacts.24666
- ESA 2026 multi-constraint hypergraph rebalancing: https://doi.org/10.4230/LIPIcs.ESA.2026.12
