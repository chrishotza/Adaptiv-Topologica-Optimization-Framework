from __future__ import annotations

import json
from pathlib import Path

from atof.routing import (
    LearnedTopologyRouter,
    evaluate_holdout_predictions,
    global_strategy_oracle,
    graph_oracle,
    routing_summary,
)
from atof.selector import HeuristicRegimeSelector
from atof.topology import TopologyProfiler
from experiments.generate_suite import build_suite
from experiments.run_canonical import run_suite


def _heuristic_strategy(graph_name: str, profiles: dict[str, dict]) -> str:
    """Map the public heuristic selector to benchmark strategy names."""
    profile_data = profiles[graph_name]
    raise RuntimeError(
        "Heuristic routing requires a TopologyProfile object; use "
        "run_routing_evaluation(), not this helper directly."
    )


def run_routing_evaluation(
    output_path: str | Path = "results/routing/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
) -> dict:
    benchmark = run_suite(
        output_path=Path(output_path).with_name("routing_input.json"),
        k=k,
        seeds=seeds,
        iterations=iterations,
    )
    rows = benchmark["rows"]
    graphs = build_suite()
    profiler = TopologyProfiler()
    selector = HeuristicRegimeSelector()

    profiles = {
        name: profiler.profile(graph)
        for name, graph in graphs.items()
    }
    topology_dicts = {
        name: profile.to_dict()
        for name, profile in profiles.items()
    }

    graph_names = sorted(graphs)
    fold_rows = []

    for held_out in graph_names:
        training_rows = [
            row for row in rows if row["graph"] != held_out
        ]
        test_rows = [
            row for row in rows if row["graph"] == held_out
        ]

        training_oracles = graph_oracle(training_rows)
        training_graphs = [
            {
                "graph": name,
                "topology": topology_dicts[name],
                "oracle_strategy": training_oracles[name],
            }
            for name in graph_names
            if name != held_out
        ]

        router = LearnedTopologyRouter().fit(training_graphs)
        learned_prediction = router.predict(topology_dicts[held_out])
        learned_eval = evaluate_holdout_predictions(
            test_rows,
            {held_out: learned_prediction},
        )[0]

        global_strategy = global_strategy_oracle(training_rows)
        global_eval = evaluate_holdout_predictions(
            test_rows,
            {held_out: global_strategy},
        )[0]

        recommendation = selector.recommend(profiles[held_out])
        heuristic_map = {
            "BLOCReloc(affinity)": "bloc_reloc_affinity",
            "BLOCReloc(baseline)": "bloc_reloc_baseline",
        }
        heuristic_prediction = heuristic_map[recommendation.primary]
        heuristic_eval = evaluate_holdout_predictions(
            test_rows,
            {held_out: heuristic_prediction},
        )[0]

        fold_rows.append(
            {
                "held_out_graph": held_out,
                "training_graphs": len(training_graphs),
                "learned_strategy": learned_eval.selected_strategy,
                "global_strategy": global_eval.selected_strategy,
                "heuristic_strategy": heuristic_eval.selected_strategy,
                "oracle_strategy": learned_eval.oracle_strategy,
                "learned_absolute_regret": learned_eval.absolute_regret,
                "global_absolute_regret": global_eval.absolute_regret,
                "heuristic_absolute_regret": heuristic_eval.absolute_regret,
                "learned_relative_regret": learned_eval.relative_regret,
                "global_relative_regret": global_eval.relative_regret,
                "heuristic_relative_regret": heuristic_eval.relative_regret,
                "topology_regime": recommendation.regime,
            }
        )

    def mean(key: str) -> float:
        values = [float(row[key]) for row in fold_rows]
        return sum(values) / len(values) if values else 0.0

    payload = {
        "schema_version": "0.1",
        "protocol": "leave-one-graph-out",
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "candidate_strategies": sorted(
            {
                row["strategy"]
                for row in rows
            }
        ),
        "graphs": graph_names,
        "folds": fold_rows,
        "summary": {
            "graphs": len(fold_rows),
            "learned_mean_absolute_regret": mean("learned_absolute_regret"),
            "global_mean_absolute_regret": mean("global_absolute_regret"),
            "heuristic_mean_absolute_regret": mean("heuristic_absolute_regret"),
            "learned_oracle_agreement": sum(
                row["learned_strategy"] == row["oracle_strategy"]
                for row in fold_rows
            ) / len(fold_rows),
            "global_oracle_agreement": sum(
                row["global_strategy"] == row["oracle_strategy"]
                for row in fold_rows
            ) / len(fold_rows),
            "heuristic_oracle_agreement": sum(
                row["heuristic_strategy"] == row["oracle_strategy"]
                for row in fold_rows
            ) / len(fold_rows),
        },
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_routing_evaluation()
    print(json.dumps(result["summary"], indent=2))
