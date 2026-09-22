from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()

    records = []
    for path in sorted(args.input_dir.rglob("access.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))

    if not records:
        raise SystemExit("no access benchmark records found")

    rows = []
    for record in records:
        repeated = record["repeated_partition_seconds"]
        rows.append({
            "tool": record["tool"],
            "description": record["description"],
            "setup_seconds": record["setup_seconds"],
            "import_seconds": record["import_seconds"],
            "first_partition_seconds": record["first_partition_seconds"],
            "steady_state_mean_seconds": sum(repeated) / len(repeated),
            "edge_cut": record["first_result"]["edge_cut"],
            "balance_error": record["first_result"]["balance_error"],
            "selected_backend": record.get("selected_backend"),
            "nodes": record["graph"]["nodes"],
            "edges": record["graph"]["edges"],
        })

    payload = {
        "schema_version": "0.1",
        "protocol": "clean-environment open-source access benchmark",
        "unit": "one isolated GitHub Actions job per tool",
        "records": rows,
        "guardrail": "No composite score or winner is produced. Setup friction and algorithmic results remain separate.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
