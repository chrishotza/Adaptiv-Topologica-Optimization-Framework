from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from atof.dynamics import summarize_trace
from atof.selector import HeuristicRegimeSelector
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler
from experiments.generate_suite import build_suite


def run_observatory(
    output_path: str | Path = "results/observatory/latest.json",
    *,
    k: int = 2,
    seeds: tuple[int, ...] = (42, 101, 2024),
    iterations: int = 25,
) -> dict:
    started = time.perf_counter()
    profiler = TopologyProfiler()
    selector = HeuristicRegimeSelector()
    rows: list[dict] = []

    for name, graph in build_suite().items():
        profile = profiler.profile(graph)
        topology = profile.to_dict()
        regime = selector.classify(profile)

        for seed in seeds:
            for variant in ("baseline", "affinity"):
                result = BLOCReloc(
                    graph,
                    k=k,
                    seed=seed,
                    variant=variant,
                ).refine(iterations=iterations)

                dynamics = summarize_trace(result.trace).to_dict()

                rows.append(
                    {
                        "graph": name,
                        "strategy": f"bloc_reloc_{variant}",
                        "seed": seed,
                        "regime": regime,
                        "edge_cut": result.edge_cut,
                        "weighted_cost": result.weighted_cost,
                        "balance_error": result.balance_error,
                        "iterations": result.iterations,
                        "topology": topology,
                        "dynamics": dynamics,
                    }
                )

    payload = {
        "schema_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": k,
        "seeds": list(seeds),
        "iterations": iterations,
        "scope": "BLOC-RELOC trace dynamics on canonical synthetic topology suite",
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_observatory()
    print(f"Generated {len(result['rows'])} observatory rows.")
