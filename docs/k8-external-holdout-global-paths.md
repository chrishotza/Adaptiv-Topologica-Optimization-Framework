# k=8 external graph holdout — frozen routing configurations

This gate moves outside the original 20-graph corpus.

## Frozen training protocol

Training uses the existing 20-graph k=8 corpus and the previously established solver seed grid:

- seeds: 42, 101, 2024
- leave the 20 training graphs unchanged
- oracle labels are computed only from training outcomes
- IQR scaling
- L2 distance

## Frozen routing configurations

Only two learned representations are tested:

- **all-features IQR/L2**
- **global-paths IQR/L2**

The fixed majority-strategy control is evaluated alongside them.

No degree/hub or hybrid retuning is introduced. Their fresh-outcome failures are already recorded as negative/inconclusive evidence.

## External holdout graphs

Four SNAP graphs not included in the 20-graph training corpus:

- ego-Facebook
- p2p-Gnutella08
- ca-AstroPh
- ca-CondMat

The official SNAP collection lists these as separate empirical networks spanning social, peer-to-peer, and scientific collaboration domains. The selected graphs range from roughly 4k to 23k nodes, keeping the gate practical while moving beyond the development/existing validation corpus.

## External outcomes

Five fresh solver seeds are frozen:

- 5003
- 7003
- 9001
- 12011
- 16001

The external solver outcomes are generated only after the routing configurations and graph list are frozen.

Primary outputs:
- graph-level mean relative regret
- 5,000-resample bootstrap CI
- paired comparison against majority control
- full external graph manifest and provenance

This is the first genuine external graph-domain holdout in the k=8 routing line.
