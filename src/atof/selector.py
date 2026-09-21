from __future__ import annotations
from dataclasses import dataclass
from .topology import TopologyProfile

@dataclass(frozen=True)
class StrategyRecommendation:
    regime: str
    primary: str
    alternatives: tuple[str, ...]
    rationale: str

class HeuristicRegimeSelector:
    """Transparent routing baseline; not a trained or validated universal policy."""
    def classify(self, profile: TopologyProfile) -> str:
        if profile.hub_ratio >= 3.0 or profile.degree_gini >= 0.45: return "hub_dominated"
        if profile.modularity == profile.modularity and profile.modularity >= 0.30: return "modular"
        if profile.degree_std <= max(profile.avg_degree * 0.20, 1.0): return "regular_like"
        return "mixed"
    def recommend(self, profile: TopologyProfile) -> StrategyRecommendation:
        regime=self.classify(profile)
        if regime=="hub_dominated": return StrategyRecommendation(regime,"BLOCReloc(affinity)",("BLOCReloc(baseline)",),"High degree heterogeneity makes degree-aware edge costs worth testing.")
        if regime=="modular": return StrategyRecommendation(regime,"BLOCReloc(baseline)",("BLOCReloc(affinity)",),"Strong community structure makes local cut refinement a natural baseline.")
        if regime=="regular_like": return StrategyRecommendation(regime,"BLOCReloc(baseline)",("BLOCReloc(affinity)",),"Homogeneous degree structure reduces the motivation for degree-weighted costs.")
        return StrategyRecommendation("mixed","BLOCReloc(baseline)",("BLOCReloc(affinity)",),"No strong structural signature was detected; compare strategies empirically.")
