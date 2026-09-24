# k=8 five-seed feature representation diagnostic

This post-hoc paired diagnostic compares the all-feature, degree/hub, mesoscopic, and global-path topology representations on the exact same five-seed solver outcomes used by the prospective degree/hub replication.

The solver outcomes are not regenerated separately for each representation. Each router is evaluated with leave-one-corpus-out training, IQR scaling, and L2 distance.

The purpose is to isolate representation effects from solver-outcome variation without changing production defaults.
