# k=8 feature-ablation diagnostic

This diagnostic reruns the frozen routing labels without rerunning any solver. It evaluates the same 20-graph k=8 outcomes under the existing routing feature-ablation definitions.

Observed on the frozen benchmark:

- all 11 features: 19.51% mean relative regret;
- without degree/hub features: 3.16%;
- without mesoscopic + global-path features, i.e. degree/hub only: 1.30%;
- without mesoscopic features: 12.66%;
- without global-path features: 98.18%;
- without degree/hub + mesoscopic: 5.80%;
- without degree/hub + global-path: 14.44%.

These are post-hoc diagnostics. The 1.30% degree/hub-only result is a candidate for a new frozen prospective experiment, not a replacement of the primary all-feature endpoint.