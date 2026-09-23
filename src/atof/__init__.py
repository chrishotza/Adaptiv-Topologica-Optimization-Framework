"""Adaptive Topological Optimization Framework."""

__version__ = "0.6.0"

from .partition import balance_error, edge_cut, initialize_balanced_partition, weighted_cut
from .strategies import BLOCReloc, PartitionResult
from .topology import TopologyProfiler, TopologyProfile
from .selector import HeuristicRegimeSelector, StrategyRecommendation
from .adaptive import (
    ControllerDecision,
    PortfolioControllerV2,
    RegimeSignatureV2,
    TrajectoryMonitor,
    TrajectoryState,
    adaptive_regime_summary,
    build_regime_signature_v2,
)
from .counterfactual import (
    CounterfactualBenchmarkResult,
    CounterfactualFold,
    leave_one_family_out,
)
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
from .product import OptimizationResult, load_graph, optimize_graph, write_partition, write_partition_mapping
from .comparison import compare_graph, compact_comparison
from .portfolio import PortfolioCandidate, PortfolioOptimizationResult, optimize_portfolio
from .backends import BackendInfo, inspect_backends
from .ai import build_ai_manifest, build_doctor_report, compact_result
from .provenance import graph_fingerprint, package_version, runtime_metadata
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
    "RegimeSignatureV2", "build_regime_signature_v2", "adaptive_regime_summary",
    "TrajectoryMonitor", "TrajectoryState",
    "PortfolioControllerV2", "ControllerDecision",
    "LearnedTopologyRouter", "NearestTopologyRouter", "RoutingEvaluation",
    "evaluate_holdout_predictions", "global_strategy_oracle",
    "graph_oracle", "routing_summary", "topology_vector",
    "CounterfactualBenchmarkResult", "CounterfactualFold", "leave_one_family_out",
    "summarize_generalization", "summarize_routing_folds", "summarize_transfer_folds",
    "GraphDataset", "standard_reference_corpus",
    "SnapDataset", "download_snap_dataset", "snap_reference_corpus", "snap_scalability_corpus",
    "OptimizationResult", "load_graph", "optimize_graph", "write_partition", "write_partition_mapping",
    "compare_graph", "compact_comparison",
    "PortfolioCandidate", "PortfolioOptimizationResult", "optimize_portfolio",
    "BackendInfo", "inspect_backends",
    "build_ai_manifest", "build_doctor_report", "compact_result",
    "graph_fingerprint", "package_version", "runtime_metadata",
    "bootstrap_mean_ci", "graph_metric_means",
    "paired_graph_differences", "paired_summary",
    "balance_error", "edge_cut", "initialize_balanced_partition",
    "weighted_cut",
]
