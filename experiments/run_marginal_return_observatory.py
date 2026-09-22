from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora
from atof.strategies import BLOCReloc

SEEDS = (42, 101, 2024)
ITERATIONS = 25
HYBRID_PERIOD = 5
BUDGETS = (25, 50, 100, 200)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _run(
    graph,
    *,
    seed: int,
    hybrid_samples: int | None,
) -> dict:
    started = time.perf_counter()
    kwargs = {}
    if hybrid_samples is not None:
        kwargs = {
            "hybrid_period": HYBRID_PERIOD,
            "hybrid_samples": hybrid_samples,
            "hybrid_policy": "fixed",
        }
    result = BLOCReloc(
        graph,
        k=2,
        seed=seed,
        variant="baseline",
    ).refine(iterations=ITERATIONS, **kwargs)

    hybrid_events = [
        event for event in result.trace if int(event["hybrid"]) == 1
    ]
    total_hybrid_gain = sum(float(event["hybrid_gain"]) for event in hybrid_events)
    total_hybrid_work = sum(int(event["hybrid_work"]) for event in hybrid_events)
    total_hybrid_passes = len(hybrid_events)

    return {
        "edge_cut": int(result.edge_cut),
        "runtime_seconds": time.perf_counter() - started,
        "hybrid_passes": total_hybrid_passes,
        "hybrid_gain": total_hybrid_gain,
        "hybrid_work": total_hybrid_work,
        "hybrid_gain_per_work": (
            total_hybrid_gain / total_hybrid_work
            if total_hybrid_work
            else 0.0
        ),
        "trace": list(result.trace),
    }


def run(
    output_path: str | Path = "results/state_of_art/marginal_return_latest.json",
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(
        cache_dir=Path(cache_dir) if cache_dir else None
    )

    rows: list[dict] = []
    baseline_cache: dict[tuple[str, int], dict] = {}

    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in SEEDS:
                key = (graph_id, seed)
                baseline = baseline_cache.get(key)
                if baseline is None:
                    baseline = _run(graph, seed=seed, hybrid_samples=None)
                    baseline_cache[key] = baseline

                for budget in BUDGETS:
                    result = _run(
                        graph,
                        seed=seed,
                        hybrid_samples=budget,
                    )
                    rows.append(
                        {
                            "corpus": corpus,
                            "graph": graph_name,
                            "graph_id": graph_id,
                            "seed": seed,
                            "budget": budget,
                            "baseline_edge_cut": baseline["edge_cut"],
                            "edge_cut": result["edge_cut"],
                            "improvement_vs_baseline": (
                                baseline["edge_cut"] - result["edge_cut"]
                            ),
                            "runtime_seconds": result["runtime_seconds"],
                            "hybrid_passes": result["hybrid_passes"],
                            "hybrid_gain": result["hybrid_gain"],
                            "hybrid_work": result["hybrid_work"],
                            "hybrid_gain_per_work": result["hybrid_gain_per_work"],
                            "trace": result["trace"],
                        }
                    )

    budget_summary = {}
    for budget in BUDGETS:
        entries = [row for row in rows if row["budget"] == budget]
        budget_summary[str(budget)] = {
            "runs": len(entries),
            "mean_edge_cut": _mean([float(r["edge_cut"]) for r in entries]),
            "mean_improvement_vs_baseline": _mean(
                [float(r["improvement_vs_baseline"]) for r in entries]
            ),
            "mean_runtime_seconds": _mean(
                [float(r["runtime_seconds"]) for r in entries]
            ),
            "mean_hybrid_work": _mean([float(r["hybrid_work"]) for r in entries]),
            "mean_hybrid_gain": _mean([float(r["hybrid_gain"]) for r in entries]),
            "mean_hybrid_gain_per_work": _mean(
                [float(r["hybrid_gain_per_work"]) for r in entries]
            ),
        }

    corpus_summary = {}
    for corpus in sorted({row["corpus"] for row in rows}):
        corpus_summary[corpus] = {}
        for budget in BUDGETS:
            entries = [
                row
                for row in rows
                if row["corpus"] == corpus and row["budget"] == budget
            ]
            corpus_summary[corpus][str(budget)] = {
                "graphs": len({row["graph_id"] for row in entries}),
                "mean_improvement_vs_baseline": _mean(
                    [float(row["improvement_vs_baseline"]) for row in entries]
                ),
                "mean_hybrid_gain_per_work": _mean(
                    [float(row["hybrid_gain_per_work"]) for row in entries]
                ),
            }

    payload = {
        "schema_version": "0.1",
        "protocol": "marginal-return observatory over fixed BLOC-RELOC hybrid budgets",
        "objective": "unweighted 2-way edge cut",
        "seeds": list(SEEDS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "budgets": list(BUDGETS),
        "rows": rows,
        "budget_summary": budget_summary,
        "corpus_summary": corpus_summary,
        "corpora": {
            corpus: {
                "graph_count": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/marginal_return_latest.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    payload = run(output_path=args.output, cache_dir=args.cache_dir)
    print(json.dumps(payload["budget_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
