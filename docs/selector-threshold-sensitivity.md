# Online selector trigger-threshold sensitivity

PR #100 fixed an oracle-free online selector: topology rank-1 is always executed, and one alternate from the rank-2/rank-3 set is probed only when training-fold statistics predict a strictly negative relative edge-cut delta.

This study varies only the minimum predicted benefit required to trigger that probe:

- 0.0000
- 0.0025
- 0.0050
- 0.0100
- 0.0200

Every threshold is evaluated independently in the same leave-one-corpus-out protocol. No result is selected automatically and no held-out oracle is used to trigger a probe.

The purpose is sensitivity analysis, not parameter tuning. Production/default behavior remains unchanged.
