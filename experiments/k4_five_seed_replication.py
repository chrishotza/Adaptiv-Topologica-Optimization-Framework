from __future__ import annotations

import argparse
from pathlib import Path

from experiments import k4_routing_generalization as base

# Independent replication protocol: same corpus, features, routing method,
# controls, and leave-one-corpus-out split; only the fixed solver seed grid
# is expanded from 3 seeds to 5.
SEEDS = (7, 42, 101, 2024, 8191)
base.SEEDS = SEEDS


def run(output_path: str | Path, cache_dir: str | Path | None = None) -> dict:
    return base.run(output_path, cache_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.output, args.cache_dir)
    import json
    print(json.dumps(result["evaluation"]["macro"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
