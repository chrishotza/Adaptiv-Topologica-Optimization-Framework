from __future__ import annotations

import argparse
import json
from collections import Counter
from math import log2
from pathlib import Path

from experiments.fresh_sota_protocol import run_benchmark
from experiments.online_topk_selector import _build_records, _evaluate
from experiments.topk_routing_coverage import _load

SEEDS = (7, 42, 101, 2024, 8191)


def _entropy(values: list[str]) -> float:
    counts = Counter(values)
    total = len(values)
    if total == 0:
        return 0.0
    return -sum(
        (count / total) * log2(count / total)
        for count in counts.values()
    )


def _seed_stability(records: list[dict]) -> dict:
    per_graph = []
    for item in records:
        oracles = list(item["seed_oracles"])
        counts = Counter(oracles)
        per_graph.append(
            {
                "graph_id": item["graph_id"],
                "stable": item["stable"],
                "seed_count": len(oracles),
                "distinct_oracle_strategies": len(counts),
                "oracle_entropy_bits": _entropy(oracles),
                "oracle_counts": dict(sorted(counts.items())),
                "seed_oracles": oracles,
            }
        )

    unstable = [row for row in per_graph if not row["stable"]]
    return {
        "graphs": len(per_graph),
        "unstable_graphs": len(unstable),
        "unstable_graph_rate": (
            len(unstable) / len(per_graph) if per_graph else 0.0
        ),
        "mean_distinct_oracle_strategies": (
            sum(row["distinct_oracle_strategies"] for row in per_graph)
            / len(per_graph)
            if per_graph
            else 0.0
        ),
        "mean_oracle_entropy_bits": (
            sum(row["oracle_entropy_bits"] for row in per_graph)
            / len(per_graph)
            if per_graph
            else 0.0
        ),
        "graph_manifest": per_graph,
    }


def run(output: Path, cache_dir: Path | None = None) -> dict:
    benchmark_path = (
        output.parent / "fresh_sota_five_seed_latest.json"
    )
    benchmark = run_benchmark(
        benchmark_path,
        seeds=SEEDS,
        cache_dir=cache_dir,
    )

    if benchmark["seeds"] != list(SEEDS):
        raise AssertionError("fresh benchmark seed manifest drifted")
    if benchmark["matched_graphs"] != 20:
        raise AssertionError("expected exactly 20 matched graphs")
    if len(benchmark["rows"]) != 20 * 11 * len(SEEDS):
        raise AssertionError("unexpected fresh benchmark row count")

    payload, rows = _load(benchmark_path)
    records = _build_records(payload, rows)
    selector = _evaluate(benchmark_path)
    stability = _seed_stability(records)

    result = {
        "schema_version": "1.0",
        "protocol": (
            "five-seed replication of the oracle-free online selector on the "
            "frozen 20-graph benchmark"
        ),
        "benchmark_commit": benchmark.get("commit_sha"),
        "seeds": list(SEEDS),
        "matched_graphs": benchmark["matched_graphs"],
        "successful_rows": len(rows),
        "selector": selector["aggregate"],
        "seed_stability": stability,
        "evidence_boundary": [
            "The graph corpus, 11-strategy portfolio, router features, predictor, and probe policy remain frozen.",
            "Only the fixed seed grid is expanded from three seeds to five seeds.",
            "All five seeds are included in the held-out evaluation of every graph.",
            "Probe decisions are still generated exclusively from leave-one-corpus-out training outcomes.",
            "The seed grid was fixed before this benchmark; no seed is selected from held-out outcomes.",
            "No production/default behavior changes.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.output, args.cache_dir)
    print(
        json.dumps(
            {
                "seeds": result["seeds"],
                "matched_graphs": result["matched_graphs"],
                "successful_rows": result["successful_rows"],
                "selector": {
                    "mean_graph_regret": result["selector"]["selector"]["mean_graph_value"],
                    "paired_delta_vs_top1": result["selector"]["paired_selector_minus_top1"]["mean"],
                    "probe_rate": result["selector"]["probe_rate"],
                    "mean_actions": result["selector"]["mean_actions"],
                },
                "seed_stability": {
                    key: value
                    for key, value in result["seed_stability"].items()
                    if key != "graph_manifest"
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
