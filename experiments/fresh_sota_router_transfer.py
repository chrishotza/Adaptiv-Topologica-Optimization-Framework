from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from atof.routing import LearnedTopologyRouter, NearestTopologyRouter
from atof.statistics import bootstrap_mean_ci


ROUTERS = ("nearest", "centroid")
CONTROLS = ("majority", "global_mean")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _load_records(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for graph_id, summary in sorted(payload["graph_summaries"].items()):
        if not summary.get("matched"):
            continue
        metadata = payload["graph_metadata"][graph_id]
        metrics = {
            strategy: {
                "edge_cut": float(values["edge_cut"]),
                "runtime_seconds": float(values["runtime_seconds"]),
            }
            for strategy, values in summary["strategies"].items()
        }
        records.append({
            "graph_id": graph_id,
            "corpus": metadata["corpus"],
            "graph": metadata["graph"],
            "topology": metadata["topology"],
            "regime_signature": metadata["regime_signature"],
            "oracle_strategy": str(summary["best_quality"]),
            "strategy_metrics": metrics,
        })
    return payload, records


def _fixed_strategy(training: list[dict], mode: str) -> str:
    if mode == "majority":
        counts = Counter(row["oracle_strategy"] for row in training)
        return min(counts, key=lambda strategy: (-counts[strategy], strategy))

    if mode == "global_mean":
        values: dict[str, list[float]] = {}
        for row in training:
            for strategy, metrics in row["strategy_metrics"].items():
                values.setdefault(strategy, []).append(float(metrics["edge_cut"]))
        return min(values, key=lambda strategy: (_mean(values[strategy]), strategy))

    raise ValueError(f"unknown control: {mode}")


def _regret(row: dict, selected: str) -> float:
    oracle = float(row["strategy_metrics"][row["oracle_strategy"]]["edge_cut"])
    value = float(row["strategy_metrics"][selected]["edge_cut"])
    return (value - oracle) / oracle if oracle else 0.0


def _runtime_ratio(row: dict, selected: str) -> float:
    runtimes = sorted(float(item["runtime_seconds"]) for item in row["strategy_metrics"].values())
    median_runtime = runtimes[len(runtimes) // 2]
    selected_runtime = float(row["strategy_metrics"][selected]["runtime_seconds"])
    return selected_runtime / median_runtime if median_runtime else 0.0


def _summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"graphs": 0}

    regret_router = [float(row["router_regret"]) for row in rows]
    regret_control = [float(row["control_regret"]) for row in rows]
    runtime_router = [float(row["router_runtime_ratio"]) for row in rows]
    runtime_control = [float(row["control_runtime_ratio"]) for row in rows]

    deltas = [a - b for a, b in zip(regret_router, regret_control)]
    runtime_deltas = [a - b for a, b in zip(runtime_router, runtime_control)]
    ci_low, ci_high = bootstrap_mean_ci(
        deltas,
        resamples=20000,
        seed=2026,
    )

    return {
        "graphs": len(rows),
        "mean_router_relative_regret": _mean(regret_router),
        "mean_control_relative_regret": _mean(regret_control),
        "mean_delta_router_minus_control": _mean(deltas),
        "bootstrap_95_ci_delta": [ci_low, ci_high],
        "mean_router_runtime_ratio": _mean(runtime_router),
        "mean_control_runtime_ratio": _mean(runtime_control),
        "mean_runtime_delta_router_minus_control": _mean(runtime_deltas),
        "router_better_graphs": sum(delta < 0 for delta in deltas),
        "router_worse_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
    }


def run_analysis(
    benchmark_path: str | Path,
    output_path: str | Path,
) -> dict:
    benchmark, records = _load_records(Path(benchmark_path))
    if len(records) < 2:
        raise ValueError("not enough matched graphs for routing transfer")

    corpora = sorted({row["corpus"] for row in records})
    oracle_distribution = {
        corpus: dict(sorted(Counter(
            row["oracle_strategy"] for row in records if row["corpus"] == corpus
        ).items()))
        for corpus in corpora
    }

    folds: dict[str, list[dict]] = {}
    for test_corpus in corpora:
        training = [row for row in records if row["corpus"] != test_corpus]
        testing = [row for row in records if row["corpus"] == test_corpus]
        if not training or not testing:
            continue

        nearest = NearestTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        centroid = LearnedTopologyRouter(scale_mode="iqr", metric="l2").fit(training)
        controls = {
            mode: _fixed_strategy(training, mode)
            for mode in CONTROLS
        }

        fold_rows = []
        for row in testing:
            predictions = {
                "nearest": nearest.predict(row["topology"]),
                "centroid": centroid.predict(row["topology"]),
            }
            for router_name, selected in predictions.items():
                for control_name, control_strategy in controls.items():
                    fold_rows.append({
                        "test_corpus": test_corpus,
                        "graph_id": row["graph_id"],
                        "oracle_strategy": row["oracle_strategy"],
                        "router": router_name,
                        "router_strategy": selected,
                        "control": control_name,
                        "control_strategy": control_strategy,
                        "router_regret": _regret(row, selected),
                        "control_regret": _regret(row, control_strategy),
                        "router_runtime_ratio": _runtime_ratio(row, selected),
                        "control_runtime_ratio": _runtime_ratio(row, control_strategy),
                    })
        folds[test_corpus] = fold_rows

    all_rows = [row for rows in folds.values() for row in rows]
    pooled = {
        f"{router}_vs_{control}": _summarize([
            row for row in all_rows
            if row["router"] == router and row["control"] == control
        ])
        for router in ROUTERS
        for control in CONTROLS
    }

    per_corpus = {
        corpus: {
            f"{router}_vs_{control}": _summarize([
                row for row in rows
                if row["router"] == router and row["control"] == control
            ])
            for router in ROUTERS
            for control in CONTROLS
        }
        for corpus, rows in folds.items()
    }

    macro = {}
    for router in ROUTERS:
        for control in CONTROLS:
            key = f"{router}_vs_{control}"
            summaries = [item[key] for item in per_corpus.values()]
            macro[key] = {
                "corpora": len(summaries),
                "mean_delta_router_minus_control": _mean([
                    item["mean_delta_router_minus_control"]
                    for item in summaries
                ]),
                "mean_router_relative_regret": _mean([
                    item["mean_router_relative_regret"]
                    for item in summaries
                ]),
                "mean_control_relative_regret": _mean([
                    item["mean_control_relative_regret"]
                    for item in summaries
                ]),
            }

    payload = {
        "schema_version": "1.0",
        "protocol": "leave-one-corpus-out solver routing on fresh 11-strategy benchmark",
        "unit_of_analysis": "graph",
        "source_benchmark": str(benchmark_path),
        "source_commit": benchmark.get("commit_sha"),
        "matched_graphs": len(records),
        "candidate_strategies": benchmark["candidate_strategies"],
        "routers": {
            "nearest": {"scale_mode": "iqr", "metric": "l2"},
            "centroid": {"scale_mode": "iqr", "metric": "l2"},
        },
        "controls": list(CONTROLS),
        "corpora": corpora,
        "oracle_distribution": oracle_distribution,
        "folds": folds,
        "pooled": pooled,
        "per_corpus": per_corpus,
        "macro": macro,
        "notes": [
            "Entire held-out corpora are excluded from router fitting and feature scaling.",
            "Router labels use only graph-level oracle strategy from the training folds.",
            "Seed-level solver outcomes are already aggregated within each graph summary.",
            "This is confirmatory transfer analysis; it does not alter the public/default router.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/fresh_router_transfer.json"),
    )
    args = parser.parse_args()
    payload = run_analysis(args.benchmark, args.output)
    print(json.dumps(payload["macro"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
