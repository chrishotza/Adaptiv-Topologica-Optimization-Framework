from __future__ import annotations

import json
from pathlib import Path

from experiments.run_canonical import run_suite
from atof.statistics import paired_summary


BASE_COMPARISONS = (
    ("bloc_reloc_affinity", "random_balanced"),
    ("bloc_reloc_baseline", "random_balanced"),
    ("bloc_reloc_affinity", "bloc_reloc_baseline"),
)


def run_statistical_analysis(
    output_path: str | Path = "results/statistics/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    resamples: int = 5000,
    bootstrap_seed: int = 2024,
) -> dict:
    """Run graph-aware paired comparisons over the canonical benchmark."""
    benchmark = run_suite(
        output_path=Path(output_path).with_name("statistics_input.json"),
        k=k,
        seeds=seeds,
        iterations=iterations,
    )
    rows = benchmark["rows"]

    comparison_specs = list(BASE_COMPARISONS)
    if k == 2:
        comparison_specs.append(
            ("bloc_reloc_affinity", "kernighan_lin")
        )

    comparisons = [
        paired_summary(
            rows,
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            metric="edge_cut",
            resamples=resamples,
            seed=bootstrap_seed,
        )
        for strategy_a, strategy_b in comparison_specs
    ]

    payload = {
        "schema_version": "0.1",
        "protocol": "graph-level paired bootstrap",
        "metric": "unweighted edge cut",
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "bootstrap": {
            "resamples": resamples,
            "confidence": 0.95,
            "seed": bootstrap_seed,
            "unit": "graph",
        },
        "comparisons": comparisons,
        "limitations": [
            "The seven-graph suite is synthetic and developmental.",
            "Confidence intervals quantify graph-level sampling uncertainty within this suite; they do not establish population-level generalization.",
            "No multiplicity adjustment is applied in this first statistical layer.",
        ],
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_statistical_analysis()
    print(json.dumps(
        {
            "comparisons": len(result["comparisons"]),
            "graphs": result["comparisons"][0]["n_graphs"],
        },
        indent=2,
    ))
