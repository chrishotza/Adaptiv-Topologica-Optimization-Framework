from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora
from experiments.run_state_of_art_benchmark import (
    ITERATIONS,
    SEEDS,
    _strategy_run,
)


def run(strategy: str, cache_dir: str | None = None) -> list[dict]:
    corpora, _ = _load_expanded_corpora(
        cache_dir=Path(cache_dir) if cache_dir else None
    )
    rows: list[dict] = []
    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in SEEDS:
                row = {
                    "corpus": corpus,
                    "graph": graph_name,
                    "graph_id": graph_id,
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "seed": seed,
                    "strategy": strategy,
                }
                try:
                    result = _strategy_run(
                        strategy,
                        graph,
                        seed=seed,
                        k=2,
                        graph_id=graph_id,
                    )
                    row.update(result)
                    row["status"] = "ok"
                except Exception as exc:
                    row.update(
                        {
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()

    rows = run(args.strategy, str(args.cache_dir) if args.cache_dir else None)
    sys.stdout.write(json.dumps(rows))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
