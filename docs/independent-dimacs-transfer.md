# Independent DIMACS transfer

This experiment tests the locked ATOF router protocol on a prespecified independent corpus from the 10th DIMACS Implementation Challenge clustering testbed.

The DIMACS source documents 30 clustering graphs from different applications and describes a standardized preprocessing into simple graph-partitioning instances. The selected six graphs are:

- jazz
- email_urv
- pgp_giant
- as_22july06
- power
- astro_ph

The subset was prespecified for application diversity and practical runtime, not by inspecting ATOF oracle outcomes.

## Protocol

- 26 total graphs across five held-out corpora.
- 9 candidate partitioning strategies, including independently validated METIS and KaHIP.
- k=2.
- Seeds: 42, 101, 2024.
- 25 BLOC-RELOC refinement iterations.
- Three previously locked router configurations:
  - all + IQR + L2
  - global paths + IQR + L2
  - global paths + min-max + L2
- True leave-one-corpus-out transfer.
- Majority control recomputed for each held-out corpus.
- No feature, scaling, metric, or router hyperparameter tuning.

## Why this is independent

The added corpus is from the DIMACS 10th Implementation Challenge clustering testbed rather than the NetworkX reference corpus or SNAP corpus already used in the 20-graph study. The six selected graph instances are not copies of the 20 existing benchmark graph names.

The DIMACS page states that its clustering testbed contains real-world graphs from different applications and gives explicit graph-level preprocessing into METIS-style partitioning inputs. citeturn802553view0turn353022view1

## Scientific question

The 20-graph run showed its strongest router-vs-majority separation on the three-graph SNAP scalability fold, especially where the majority strategy incurred nonzero regret. This run asks whether the same locked topology representation transfers to an independent graph-partitioning corpus without retuning.

A positive result would be evidence of transfer to a new corpus family; a null or negative result would constrain the scalability-fold interpretation.

No public/default router change is implied by this experiment.
