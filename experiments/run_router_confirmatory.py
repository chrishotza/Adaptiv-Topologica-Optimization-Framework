from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from atof.routing import FEATURE_GROUPS
from experiments.run_router_scaling_ablation import (
    _benchmark_graph,
    _load_corpora,
    _run_config,
)


LOCKED_CONFIGS = {
    "all_iqr_l2": (FEATURE_GROUPS["all"], "iqr", "l2"),
    "global_paths_iqr_l2": (FEATURE_GROUPS["global_paths"], "iqr", "l2"),
    "global_paths_minmax_l2": (FEATURE_GROUPS["global_paths"], "minmax", "l2"),
}


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_confirmatory(
    output_path: str | Path = "results/generalization/router_confirmatory.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
    cache_dir: str | Path | None = None,
) -> dict:
    if k != 2:
        raise ValueError("The confirmatory protocol currently requires k=2.")
    if not seeds:
        raise ValueError("seeds must not be empty")

    started = time.perf_counter()
    corpora, provenance = _load_corpora(cache_dir=cache_dir)
    records = {
        corpus: {
            name: _benchmark_graph(
                graph,
                corpus=corpus,
                name=name,
                k=k,
                seeds=seeds,
                iterations=iterations,
            )
            for name, graph in graphs.items()
        }
        for corpus, graphs in corpora.items()
    }

    configs = {
        name: _run_config(records, *config)
        for name, config in LOCKED_CONFIGS.items()
    }

    payload = {
        "schema_version": "0.1",
        "protocol": "locked confirmatory comparison of pre-registered routing configurations",
        "unit_of_analysis": "held-out graph",
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "locked_configs": {
            name: {
                "features": list(config[0]),
                "scale_mode": config[1],
                "metric": config[2],
            }
            for name, config in LOCKED_CONFIGS.items()
        },
        "configs": configs,
        "corpora": {
            corpus: {
                "graphs": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "interpretation": [
            "The three routing configurations are locked before execution from the previous scaling ablation.",
            "No feature, scaler, or metric selection is optimized on this run.",
            "The majority control remains embedded in every configuration for direct comparison.",
            "This is confirmatory validation of previously observed candidates, not a new tuning sweep.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_confirmatory()
    print(
        json.dumps(
            {name: value["macro"] for name, value in result["configs"].items()},
            indent=2,
        )
    )
