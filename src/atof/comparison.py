from __future__ import annotations

from typing import Any

import networkx as nx

from . import __version__
from .portfolio import optimize_portfolio
from .product import optimize_graph
from .provenance import graph_fingerprint


def compare_graph(
    graph: nx.Graph,
    *,
    k: int = 2,
    seed: int = 42,
    iterations: int = 25,
) -> dict[str, Any]:
    """Run the native Engine and Portfolio under identical product parameters."""
    engine = optimize_graph(
        graph,
        k=k,
        seed=seed,
        iterations=iterations,
        variant="auto",
    )
    portfolio = optimize_portfolio(
        graph,
        k=k,
        seed=seed,
        iterations=iterations,
    )

    engine_payload = engine.to_dict(include_partition=False)
    portfolio_payload = portfolio.to_dict(include_partition=False)

    engine_edge_cut = int(engine_payload["result"]["edge_cut"])
    portfolio_edge_cut = int(portfolio_payload["result"]["edge_cut"])
    engine_balance = float(engine_payload["result"]["balance_error"])
    portfolio_balance = float(portfolio_payload["result"]["balance_error"])

    if engine_edge_cut < portfolio_edge_cut:
        lower_edge_cut = "engine"
    elif portfolio_edge_cut < engine_edge_cut:
        lower_edge_cut = "portfolio"
    else:
        lower_edge_cut = "tie"

    return {
        "schema": "atof.compare.v1",
        "version": __version__,
        "mode": "compare",
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
        "parameters": {
            "k": k,
            "seed": seed,
            "iterations": iterations,
        },
        "comparison": {
            "edge_cut_delta": portfolio_edge_cut - engine_edge_cut,
            "balance_error_delta": portfolio_balance - engine_balance,
            "lower_edge_cut": lower_edge_cut,
            "selection_metric": "observed unweighted edge_cut",
            "interpretation": (
                "comparison describes the observed outputs under identical "
                "parameters; it does not claim global optimality"
            ),
        },
        "engine": {
            "schema": engine_payload["schema"],
            "strategy": engine_payload["strategy"],
            "objective": engine_payload["objective"],
            "result": engine_payload["result"],
        },
        "portfolio": {
            "schema": portfolio_payload["schema"],
            "strategy": portfolio_payload["strategy"],
            "objective": portfolio_payload["objective"],
            "result": portfolio_payload["result"],
            "candidates": portfolio_payload["candidates"],
        },
        "provenance": {
            "graph_fingerprint": graph_fingerprint(graph),
            "seed": seed,
            "iterations": iterations,
        },
    }


def compact_comparison(payload: dict[str, Any]) -> dict[str, Any]:
    """Reduce a comparison result for low-token agent orchestration."""
    return {
        "schema": payload["schema"],
        "version": payload["version"],
        "mode": payload["mode"],
        "graph": payload["graph"],
        "parameters": payload["parameters"],
        "comparison": payload["comparison"],
        "engine": {
            "schema": payload["engine"]["schema"],
            "strategy": payload["engine"]["strategy"],
            "result": payload["engine"]["result"],
        },
        "portfolio": {
            "schema": payload["portfolio"]["schema"],
            "strategy": payload["portfolio"]["strategy"],
            "result": payload["portfolio"]["result"],
            "candidates": [
                {
                    "id": candidate["id"],
                    "available": candidate["available"],
                    "edge_cut": candidate["edge_cut"],
                    "balance_error": candidate["balance_error"],
                    "runtime_seconds": candidate["runtime_seconds"],
                    "error": candidate["error"],
                }
                for candidate in payload["portfolio"]["candidates"]
            ],
        },
        "provenance": payload["provenance"],
    }
