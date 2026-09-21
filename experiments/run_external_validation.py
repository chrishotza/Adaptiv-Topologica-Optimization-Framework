from __future__ import annotations

import json
import math
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from atof.datasets import standard_reference_corpus
from atof.routing import (
    LearnedTopologyRouter,
    evaluate_holdout_predictions,
    graph_oracle,
    global_strategy_oracle,
)
from atof.selector import HeuristicRegimeSelector
from atof.statistics import paired_summary
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler
from experiments.run_canonical import (
    balanced_round_robin,
    kernighan_lin,
    random_balanced,
    spectral_bisection,
)


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _safe_profile(graph: nx.Graph) -> dict:
    profile = TopologyProfiler().profile(graph).to_dict()
    return {
        key: (None if isinstance(value, float) and math.isnan(value) else value)
        for key, value in profile.items()
    }


def run_external_validation(
    output_path: str | Path = "results/external/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    bootstrap_resamples: int = 5000,
) -> dict:
    """Run the same two-way benchmark protocol over standard reference graphs."""
    if k != 2:
        raise ValueError("The external protocol currently requires k=2.")

    started = time.perf_counter()
    selector = HeuristicRegimeSelector()
    profiler = TopologyProfiler()

    datasets = standard_reference_corpus()
    graphs = {dataset.name: dataset.load() for dataset in datasets}
    rows: list[dict] = []

    for dataset in datasets:
        graph = graphs[dataset.name]
        profile = profiler.profile(graph)
        topology = _safe_profile(graph)
        regime = selector.classify(profile)
        common = {
            "graph": dataset.name,
            "regime": regime,
            **topology,
        }

        for seed in seeds:
            rows.append(
                {
                    **common,
                    "strategy": "round_robin",
                    "seed": seed,
                    **balanced_round_robin(graph, k),
                }
            )
            rows.append(
                {
                    **common,
                    "strategy": "random_balanced",
                    "seed": seed,
                    **random_balanced(graph, k, seed),
                }
            )

            for variant in ("baseline", "affinity"):
                result = BLOCReloc(
                    graph,
                    k=k,
                    seed=seed,
                    variant=variant,
                ).refine(iterations=iterations)
                rows.append(
                    {
                        **common,
                        "strategy": f"bloc_reloc_{variant}",
                        "seed": seed,
                        "edge_cut": result.edge_cut,
                        "weighted_cost": result.weighted_cost,
                        "balance_error": result.balance_error,
                        "iterations": result.iterations,
                    }
                )

            rows.append(
                {
                    **common,
                    "strategy": "spectral_bisection",
                    "seed": seed,
                    **spectral_bisection(graph),
                }
            )
            rows.append(
                {
                    **common,
                    "strategy": "kernighan_lin",
                    "seed": seed,
                    **kernighan_lin(graph, seed),
                }
            )

    routing_folds: list[dict] = []
    graph_names = sorted(graphs)

    for held_out in graph_names:
        training_rows = [row for row in rows if row["graph"] != held_out]
        test_rows = [row for row in rows if row["graph"] == held_out]
        oracle_labels = graph_oracle(training_rows)
        training_graphs = [
            {
                "graph": name,
                "topology": _safe_profile(graphs[name]),
                "oracle_strategy": oracle_labels[name],
            }
            for name in graph_names
            if name != held_out
        ]

        router = LearnedTopologyRouter().fit(training_graphs)
        learned_prediction = router.predict(_safe_profile(graphs[held_out]))
        learned_eval = evaluate_holdout_predictions(
            test_rows, {held_out: learned_prediction}
        )[0]

        fixed_prediction = global_strategy_oracle(training_rows)
        fixed_eval = evaluate_holdout_predictions(
            test_rows, {held_out: fixed_prediction}
        )[0]

        recommendation = selector.recommend(profiler.profile(graphs[held_out]))
        heuristic_map = {
            "BLOCReloc(affinity)": "bloc_reloc_affinity",
            "BLOCReloc(baseline)": "bloc_reloc_baseline",
        }
        heuristic_prediction = heuristic_map[recommendation.primary]
        heuristic_eval = evaluate_holdout_predictions(
            test_rows, {held_out: heuristic_prediction}
        )[0]

        routing_folds.append(
            {
                "held_out_graph": held_out,
                "training_graphs": len(training_graphs),
                "learned_strategy": learned_eval.selected_strategy,
                "global_strategy": fixed_eval.selected_strategy,
                "heuristic_strategy": heuristic_eval.selected_strategy,
                "oracle_strategy": learned_eval.oracle_strategy,
                "learned_absolute_regret": learned_eval.absolute_regret,
                "global_absolute_regret": fixed_eval.absolute_regret,
                "heuristic_absolute_regret": heuristic_eval.absolute_regret,
                "learned_relative_regret": learned_eval.relative_regret,
                "global_relative_regret": fixed_eval.relative_regret,
                "heuristic_relative_regret": heuristic_eval.relative_regret,
            }
        )

    comparisons = [
        paired_summary(
            rows,
            strategy_a=a,
            strategy_b=b,
            metric="edge_cut",
            resamples=bootstrap_resamples,
            seed=2024,
        )
        for a, b in (
            ("bloc_reloc_affinity", "random_balanced"),
            ("bloc_reloc_baseline", "random_balanced"),
            ("bloc_reloc_affinity", "kernighan_lin"),
            ("spectral_bisection", "kernighan_lin"),
        )
    ]

    learned_agreement = sum(
        row["learned_strategy"] == row["oracle_strategy"]
        for row in routing_folds
    ) / len(routing_folds)

    payload = {
        "schema_version": "0.1",
        "protocol": "standard external reference corpus; graph-level paired benchmark and leave-one-graph-out routing",
        "corpus_type": "standard_reference_graphs",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "commit_sha": _commit_sha(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "graphs": {
            dataset.name: {
                "nodes": graphs[dataset.name].number_of_nodes(),
                "edges": graphs[dataset.name].number_of_edges(),
                "source": dataset.source,
                "reference_url": dataset.reference_url,
                "notes": dataset.notes,
            }
            for dataset in datasets
        },
        "rows": rows,
        "comparisons": comparisons,
        "routing": {
            "protocol": "leave-one-graph-out",
            "graphs": len(routing_folds),
            "folds": routing_folds,
            "learned_oracle_agreement": learned_agreement,
        },
        "limitations": [
            "The reference corpus contains four small standard graphs and is not a representative sample of all graph populations.",
            "The benchmark uses unweighted edge cut even for datasets that contain edge weights.",
            "Bootstrap intervals quantify uncertainty across these four graphs only.",
            "The routing result is an exploratory leave-one-graph-out evaluation with a small training corpus.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_external_validation()
    print(
        json.dumps(
            {
                "graphs": len(result["graphs"]),
                "rows": len(result["rows"]),
                "learned_oracle_agreement": result["routing"]["learned_oracle_agreement"],
            },
            indent=2,
        )
    )
