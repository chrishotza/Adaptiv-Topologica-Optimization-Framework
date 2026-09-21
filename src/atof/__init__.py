"""Adaptive Topological Optimization Framework."""

from .partition import balance_error, edge_cut, initialize_balanced_partition, weighted_cut
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfiler, TopologyProfile
from .selector import HeuristicRegimeSelector, StrategyRecommendation
from .routing import (
    LearnedTopologyRouter,
    RoutingEvaluation,
    evaluate_holdout_predictions,
    global_strategy_oracle,
    graph_oracle,
    routing_summary,
    topology_vector,
)

__all__ = [
    "BLOCReloc", "PartitionResult",
    "TopologyProfiler", "TopologyProfile",
    "HeuristicRegimeSelector", "StrategyRecommendation",
    "LearnedTopologyRouter", "RoutingEvaluation",
    "evaluate_holdout_predictions", "global_strategy_oracle",
    "graph_oracle", "routing_summary", "topology_vector",
    "balance_error", "edge_cut", "initialize_balanced_partition",
    "weighted_cut",
]

__version__ = "0.2.0"
