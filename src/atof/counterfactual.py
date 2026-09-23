from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Mapping, Sequence

from .routing import (
    LearnedTopologyRouter,
    NearestTopologyRouter,
    RoutingEvaluation,
    evaluate_holdout_predictions,
    routing_summary,
)


@dataclass(frozen=True)
class CounterfactualFold:
    holdout_family: str
    train_graphs: tuple[str, ...]
    holdout_graphs: tuple[str, ...]
    evaluations: tuple[RoutingEvaluation, ...]
    summary: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "holdout_family": self.holdout_family,
            "train_graphs": list(self.train_graphs),
            "holdout_graphs": list(self.holdout_graphs),
            "evaluations": [item.to_dict() for item in self.evaluations],
            "summary": dict(self.summary),
        }


@dataclass(frozen=True)
class CounterfactualBenchmarkResult:
    router_name: str
    family_count: int
    graph_count: int
    no_lookahead: bool
    folds: tuple[CounterfactualFold, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "atof.counterfactual.v1",
            "router": self.router_name,
            "family_count": self.family_count,
            "graph_count": self.graph_count,
            "no_lookahead": self.no_lookahead,
            "folds": [fold.to_dict() for fold in self.folds],
        }


def leave_one_family_out(
    rows: Sequence[Mapping],
    *,
    family_by_graph: Mapping[str, str],
    router_factory: Callable[[], object] | None = None,
) -> CounterfactualBenchmarkResult:
    """Evaluate routing with graph-family holdout and no look-ahead.

    Each held-out family is excluded completely from router fitting. The
    oracle labels used for evaluation are read only from held-out rows after
    prediction, so they cannot influence training or policy selection.
    """
    if not rows:
        raise ValueError("rows must not be empty")
    if not family_by_graph:
        raise ValueError("family_by_graph must not be empty")

    graph_names = {str(row["graph"]) for row in rows}
    missing = sorted(graph for graph in graph_names if graph not in family_by_graph)
    if missing:
        raise ValueError(
            "family_by_graph is missing graph labels: " + ", ".join(missing)
        )

    families = sorted({str(family_by_graph[graph]) for graph in graph_names})
    if len(families) < 2:
        raise ValueError("at least two graph families are required")

    if router_factory is None:
        router_factory = lambda: NearestTopologyRouter()

    folds: list[CounterfactualFold] = []
    for held_out_family in families:
        train = [
            row for row in rows
            if str(family_by_graph[str(row["graph"])]) != held_out_family
        ]
        holdout = [
            row for row in rows
            if str(family_by_graph[str(row["graph"])]) == held_out_family
        ]

        train_graphs = {str(row["graph"]) for row in train}
        holdout_graphs = {str(row["graph"]) for row in holdout}
        if train_graphs.intersection(holdout_graphs):
            raise AssertionError("counterfactual split leaked graph identities")
        if not train_graphs or not holdout_graphs:
            raise ValueError(f"family split is empty for {held_out_family}")

        router = router_factory()
        if not hasattr(router, "fit") or not hasattr(router, "predict"):
            raise TypeError("router_factory must produce an object with fit() and predict()")
        router.fit(train)

        predictions = {
            graph: router.predict(next(row["topology"] for row in holdout if str(row["graph"]) == graph))
            for graph in sorted(holdout_graphs)
        }
        evaluations = tuple(
            evaluate_holdout_predictions(holdout, predictions)
        )
        folds.append(
            CounterfactualFold(
                holdout_family=held_out_family,
                train_graphs=tuple(sorted(train_graphs)),
                holdout_graphs=tuple(sorted(holdout_graphs)),
                evaluations=evaluations,
                summary=routing_summary(evaluations),
            )
        )

    return CounterfactualBenchmarkResult(
        router_name=type(router_factory()).__name__,
        family_count=len(families),
        graph_count=len(graph_names),
        no_lookahead=True,
        folds=tuple(folds),
    )
