from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

EXTERNAL = (
    "metis",
    "kahip",
    "kaminpar_default",
    "kaminpar_strong",
    "mtkahypar_default",
    "mtkahypar_quality",
)


def analyze(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []

    for graph_id, summary in payload["graph_summaries"].items():
        strategies = summary["strategies"]
        baseline = float(strategies["bloc_reloc_baseline"]["edge_cut"])
        hybrid = float(strategies["bloc_reloc_hybrid_fixed"]["edge_cut"])
        external_best = min(float(strategies[name]["edge_cut"]) for name in EXTERNAL)
        denominator = baseline - external_best
        recovery = None if denominator <= 0 else (baseline - hybrid) / denominator
        residual = 0.0 if denominator <= 0 else (hybrid - external_best) / denominator
        corpus = graph_id.split("/", 1)[0]
        rows.append(
            {
                "graph_id": graph_id,
                "corpus": corpus,
                "baseline_edge_cut": baseline,
                "hybrid_edge_cut": hybrid,
                "external_best_edge_cut": external_best,
                "gap_recovery_fraction": recovery,
                "gap_residual_fraction": residual,
            }
        )

    by_corpus: dict[str, dict] = {}
    for corpus in sorted({row["corpus"] for row in rows}):
        values = [row["gap_recovery_fraction"] for row in rows if row["corpus"] == corpus and row["gap_recovery_fraction"] is not None]
        residuals = [row["gap_residual_fraction"] for row in rows if row["corpus"] == corpus]
        by_corpus[corpus] = {
            "graphs": len(values),
            "mean_gap_recovery_percent": 100.0 * statistics.fmean(values) if values else 0.0,
            "median_gap_recovery_percent": 100.0 * statistics.median(values) if values else 0.0,
            "mean_gap_residual_percent": 100.0 * statistics.fmean(residuals) if residuals else 0.0,
        }

    rows.sort(key=lambda row: (
        float("inf") if row["gap_recovery_fraction"] is None else row["gap_recovery_fraction"]
    ))

    return {
        "source_commit": payload.get("commit_sha"),
        "graphs": len(rows),
        "overall_mean_gap_recovery_percent": 100.0 * statistics.fmean(
            row["gap_recovery_fraction"]
            for row in rows
            if row["gap_recovery_fraction"] is not None
        ),
        "overall_median_gap_recovery_percent": 100.0 * statistics.median(
            row["gap_recovery_fraction"]
            for row in rows
            if row["gap_recovery_fraction"] is not None
        ),
        "by_corpus": by_corpus,
        "lowest_recovery": rows[:8],
        "highest_recovery": list(reversed(rows[-8:])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = analyze(args.input)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
