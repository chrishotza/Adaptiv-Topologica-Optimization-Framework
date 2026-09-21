"""Adaptive Topological Optimization Framework."""

from .partition import balance_error, edge_cut, initialize_balanced_partition, weighted_cut
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfiler, TopologyProfile
from .selector import HeuristicRegimeSelector, StrategyRecommendation
from .snap import SnapDataset, download_snap_dataset, snap_reference_corpus, snap_scalability_corpus
from .routing import (
    LearnedTopologyRouter,
    NearestTopologyRouter,
    RoutingEvaluation,
    evaluate_holdout_predictions,
    global_strategy_oracle,
    graph_oracle,
    routing_summary,
    topology_vector,
)
from .generalization import (
    summarize_generalization,
    summarize_routing_folds,
    summarize_transfer_folds,
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
    "LearnedTopologyRouter", "NearestTopologyRouter", "RoutingEvaluation",
    "evaluate_holdout_predictions", "global_strategy_oracle",
    "graph_oracle", "routing_summary", "topology_vector",
    "summarize_generalization", "summarize_routing_folds", "summarize_transfer_folds",
    "GraphDataset", "standard_reference_corpus",
    "SnapDataset", "download_snap_dataset", "snap_reference_corpus", "snap_scalability_corpus",
    "bootstrap_mean_ci", "graph_metric_means",
    "paired_graph_differences", "paired_summary",
    "balance_error", "edge_cut", "initialize_balanced_partition",
    "weighted_cut",
]

__version__ = "0.5.0"
