from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


def summarize(
    input_path: str | Path = "results/canonical/latest.json",
    output_path: str | Path = "results/canonical/summary.csv",
) -> list[dict]:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in payload["rows"]:
        grouped[(row["graph"], row["strategy"])].append(float(row["edge_cut"]))

    rows = []
    for (graph, strategy), values in sorted(grouped.items()):
        rows.append(
            {
                "graph": graph,
                "strategy": strategy,
                "runs": len(values),
                "mean_edge_cut": sum(values) / len(values),
                "min_edge_cut": min(values),
                "max_edge_cut": max(values),
            }
        )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return rows


if __name__ == "__main__":
    rows = summarize()
    print(f"Wrote {len(rows)} grouped benchmark summaries.")
