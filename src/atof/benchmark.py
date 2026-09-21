from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

import networkx as nx

from .strategies import BLOCReloc


def benchmark_bloc(
    graphs: Iterable[tuple[str, nx.Graph]],
    *,
    k: int = 4,
    seeds: Iterable[int] = (42, 101, 2024),
    iterations: int = 25,
) -> list[dict]:
    """Run canonical BLOC-RELOC variants and return serializable records."""
    rows: list[dict] = []

    for name, graph in graphs:
        for variant in ("baseline", "affinity"):
            for seed in seeds:
                result = BLOCReloc(
                    graph, k=k, seed=seed, variant=variant
                ).refine(iterations=iterations)

                row = asdict(result)
                row.pop("partition", None)
                row["trace"] = list(result.trace)
                row.update({"graph": name, "variant": variant, "seed": seed})
                rows.append(row)

    return rows
