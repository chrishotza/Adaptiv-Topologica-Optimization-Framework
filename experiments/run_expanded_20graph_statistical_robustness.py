from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def percentile(values, p):
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def bootstrap_mean_ci(values, resamples=20_000, seed=2024):
    rng = random.Random(seed)
    n = len(values)
    samples = [
        mean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(resamples)
    ]
    return percentile(samples, 0.025), percentile(samples, 0.975)


def exact_sign_test(values):
    values = [v for v in values if abs(v) > 1e-15]
    n = len(values)
    if not n:
        return 1.0
    negatives = sum(v < 0 for v in values)
    tail = min(negatives, n - negatives)
    return min(
        1.0,
        2.0 * sum(math.comb(n, i) for i in range(tail + 1)) / (2 ** n),
    )


def folds(cfg):
    return [f for fs in cfg["folds"].values() for f in fs]


def paired_vs_majority(cfg, key):
    rows = folds(cfg)
    delta = [r[key] - r["majority_relative_regret"] for r in rows]
    low, high = bootstrap_mean_ci(delta)
    return {
        "graph_n": len(delta),
        "router_mean": mean(r[key] for r in rows),
        "majority_mean": mean(r["majority_relative_regret"] for r in rows),
        "mean_delta_router_minus_majority": mean(delta),
        "bootstrap_ci_95": {"lower": low, "upper": high, "resamples": 20_000, "seed": 2024},
        "router_better_graphs": sum(v < 0 for v in delta),
        "router_worse_graphs": sum(v > 0 for v in delta),
        "ties": sum(abs(v) <= 1e-15 for v in delta),
        "exact_two_sided_sign_p": exact_sign_test(delta),
    }


def corpus_deltas(cfg, key):
    out = []
    for corpus, summary in cfg["corpora"].items():
        router = summary[key]
        majority = summary["majority_mean_relative_regret"]
        out.append({
            "corpus": corpus,
            "router": router,
            "majority": majority,
            "delta_router_minus_majority": router - majority,
            "graphs": summary["graphs"],
        })
    return out


def main(input_path, output_path):
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if source.get("total_graphs") != 20 or source.get("candidate_strategy_count") != 9:
        raise ValueError("expected the 20-graph nine-strategy transfer artifact")

    result = {
        "schema_version": "1.0",
        "protocol": "expanded 20-graph paired statistical robustness",
        "source": {
            "workflow_run": 35628301069,
            "job": 106428005350,
            "artifact_id": 10654092095,
            "artifact_sha256": "da24794b66dfae15c0ecc02dffad0471d63100cc0f01d3a9f5db0635ab39a542",
            "commit_sha": source["commit_sha"],
        },
        "bootstrap": {"resamples": 20_000, "confidence": 0.95, "seed": 2024},
        "interpretation": [
            "Relative regret is lower-is-better.",
            "Graph-level paired deltas are router minus majority; negative favors the router.",
            "Protocol macro regret is fold-balanced across four held-out corpora; graph-level means weight all 20 graphs equally.",
            "The four corpus-level comparisons are descriptive because there are only four held-out corpora.",
            "Bootstrap intervals are uncertainty estimates under the stated resampling scheme, not population guarantees.",
        ],
        "configs": {},
    }

    for name, cfg in source["configs"].items():
        result["configs"][name] = {
            "protocol_macro": cfg["macro"],
            "graph_level_vs_majority": {
                "centroid": paired_vs_majority(cfg, "learned_relative_regret"),
                "nearest": paired_vs_majority(cfg, "nearest_relative_regret"),
            },
            "corpus_level_centroid_vs_majority": corpus_deltas(
                cfg, "learned_mean_relative_regret"
            ),
        }

    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_expanded_20graph_statistical_robustness.py INPUT_JSON OUTPUT_JSON")
    main(sys.argv[1], sys.argv[2])
