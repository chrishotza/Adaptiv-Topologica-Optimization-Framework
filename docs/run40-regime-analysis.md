# Run #40 regime analysis

## What the metric means

For each graph, define the mature-external reference as the best mean edge cut among METIS, KaHIP, KaMinPar default/strong, and Mt-KaHyPar default/quality.

Define hybrid gap recovery as:

`(BLOC baseline cut - BLOC hybrid cut) / (BLOC baseline cut - mature-external cut)`.

A value of 100% would mean that hybrid refinement closes the entire gap to the best mature external solver on that graph. A value near 0% means that the hybrid intervention barely moves toward the mature external result.

## Corpus-level result

The mean recovery across 19 non-degenerate graphs is **48.56%**; the median is **58.93%**.

| Corpus | Graphs | Mean recovery | Mean residual gap |
|---|---:|---:|---:|
| Development | 7 | 76.63% | 23.37% |
| External | 3 | 74.99% | 18.76% |
| SNAP routine | 6 | 24.86% | 75.14% |
| SNAP scalability | 3 | 4.01% | 95.99% |

The pattern is stronger than the single aggregate: hybrid refinement is effective on the development and small external corpus, but its ability to close the mature-solver gap collapses on routine and scalability SNAP graphs.

## Hard cases

The five lowest recovery cases are ca-HepTh (1.15%), CollegeMsg (1.93%), ca-GrQc (4.35%), email-Eu-core (4.72%), and Wiki-Vote (6.54%).

The five highest are Karate Club (83.91%), cycle (82.80%), Davis Southern Women (82.14%), path (81.72%), and Barabási-Albert (80.00%).

## Research implication

This is exactly the structure a dynamic controller should exploit.

On graphs where hybrid recovery is already high, additional hybrid budget has diminishing value because the controller is close to the mature external frontier. On the low-recovery SNAP/scalability graphs, simply spending more of the same two-swap budget is unlikely to close the remaining gap efficiently; the controller should instead detect the low marginal return and switch neighborhoods, initializers, or solver families.

This turns the research problem from a generic 'adaptive hybrid' into a measurable online decision problem:

- estimate marginal cut improvement per unit structural work;
- identify the point of diminishing return for the current operator;
- allocate the next budget block to a complementary operator;
- preserve a no-regression gate when the new operator cannot justify its cost.

That will be the basis of the next dynamic compute-allocation experiment.

## Provenance

Source: GitHub Actions `State-of-art benchmark #40`, 20 graphs, 3 seeds, 11 candidates. Machine-readable summary: `results/state_of_art/run40_summary.json`.