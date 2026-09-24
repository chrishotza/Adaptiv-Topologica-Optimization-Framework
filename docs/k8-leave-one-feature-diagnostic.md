# k=8 leave-one-feature routing diagnostic

This post-hoc diagnostic removes each topology feature in turn from the original 11-feature k=8 router and evaluates the resulting routing on the identical five-seed solver outcomes used by the degree/hub replication.

The purpose is to identify which individual features are responsible for the large routing failures exposed by the degree/hub configuration.

No production/default router behavior is changed.
