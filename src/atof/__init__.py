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
from .datasets import GraphDataset, standard_reference_corpus
from .statistics import (
    bootstrap_mean_ci,
    graph_metric_means,
    paired_graph_differences,
    paired_summary,
)

__all__ = [
    "BLOCReloc", "PartitionResult",
    "TopologyProfiler", "TopologyProfile",
    "HeuristicRegimeSelector", "StrategyRecommendation",
    "LearnedTopologyRouter", "RoutingEvaluation",
    "evaluate_holdout_predictions", "global_strategy_oracle",
    "graph_oracle", "routing_summary", "topology_vector",
    "GraphDataset", "standard_reference_corpus",
    "bootstrap_mean_ci", "graph_metric_means",
    "paired_graph_differences", "paired_summary",
    "balance_error", "edge_cut", "initialize_balanced_partition",
    "weighted_cut",
]

__version__ = "0.3.0"
