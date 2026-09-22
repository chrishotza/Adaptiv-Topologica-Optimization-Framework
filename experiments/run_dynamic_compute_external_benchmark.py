from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from atof.statistics import paired_summary
from atof.strategies import BLOCReloc
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora


SEEDS = (42, 101, 2024)
ITERATIONS = 25
HYBRID_PERIOD = 5
HYBRID_SAMPLES = 100
POLICIES = ("off", "fixed", "adaptive", "marginal")


def _commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _expected_balance_error(graph, k: int) -> float:
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    lower = n // k
    upper = (n + k - 1) // k
    target = n / k
    return max(abs(lower - target), abs(upper - target)) / target


def _validate_exact_balance_error(
    graph,
    k: int,
    balance_error: float,
) -> bool:
    return abs(
        balance_error - _expected_balance_error(graph, k)
    ) <= 1e-12


def _run_policy(graph, *, seed: int, policy: str) -> dict:
    kwargs = {
        "iterations": ITERATIONS,
    }
    if policy != "off":
        kwargs.update(
            {
                "hybrid_period": HYBRID_PERIOD,
                "hybrid_samples": HYBRID_SAMPLES,
                "hybrid_policy": policy,
                "hybrid_probe_samples": 20,
                "hybrid_witness_patience": 2,
            }
        )

    started = time.perf_counter()
    result = BLOCReloc(
        graph,
        k=2,
        seed=seed,
        variant="baseline",
    ).refine(**kwargs)
    wall_runtime = time.perf_counter() - started
    total_work = sum(int(event["total_work"]) for event in result.trace)
    probe_work = sum(int(event["probe_work"]) for event in result.trace)
    cumulative_work = 0
    work_curve = []
    for event in result.trace:
        cumulative_work += int(event["total_work"])
        work_curve.append(
            {
                "work": cumulative_work,
                "edge_cut": int(event["edge_cut"]),
            }
        )

    balance = float(result.balance_error)
    if not _validate_exact_balance_error(graph, 2, balance):
        raise ValueError(
            "BLOC-RELOC returned a partition outside the exact "
            "floor/ceil balance contract"
        )

    return {
        "nodes": int(graph.number_of_nodes()),
        "edges": int(graph.number_of_edges()),
        "edge_cut": int(result.edge_cut),
        "balance_error": balance,
        "total_work": int(total_work),
        "probe_work": int(probe_work),
        "work_curve": work_curve,
        "hybrid_passes": int(result.hybrid_passes),
        "hybrid_probes": int(result.hybrid_probes),
        "runtime_seconds": wall_runtime,
    }


def _policy_summary(rows: list[dict], policy: str) -> dict:
    selected = [row for row in rows if row["strategy"] == policy]
    graph_count = len({row["graph_id"] for row in selected})
    return {
        "graphs": graph_count,
        "rows": len(selected),
        "mean_edge_cut": (
            sum(float(row["edge_cut"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_total_work": (
            sum(float(row["total_work"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_runtime_seconds": (
            sum(float(row["runtime_seconds"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_hybrid_passes": (
            sum(float(row["hybrid_passes"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
        "mean_probe_work": (
            sum(float(row["probe_work"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
    }


def _graph_policy_means(rows: list[dict], policy: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if row["strategy"] != policy:
            continue
        grouped.setdefault(str(row["graph_id"]), []).append(row)

    return {
        graph_id: {
            "edge_cut": sum(float(row["edge_cut"]) for row in values) / len(values),
            "total_work": sum(float(row["total_work"]) for row in values) / len(values),
        }
        for graph_id, values in grouped.items()
    }


def _dominance_vs_fixed(rows: list[dict], policy: str) -> dict:
    fixed = _graph_policy_means(rows, "fixed")
    candidate = _graph_policy_means(rows, policy)
    graphs = sorted(set(fixed) & set(candidate))
    dominated = []
    quality_better = []
    work_lower = []
    for graph_id in graphs:
        f = fixed[graph_id]
        c = candidate[graph_id]
        quality_ok = c["edge_cut"] <= f["edge_cut"]
        work_ok = c["total_work"] <= f["total_work"]
        strict = (
            c["edge_cut"] < f["edge_cut"]
            or c["total_work"] < f["total_work"]
        )
        if quality_ok and c["edge_cut"] < f["edge_cut"]:
            quality_better.append(graph_id)
        if work_ok and c["total_work"] < f["total_work"]:
            work_lower.append(graph_id)
        if quality_ok and work_ok and strict:
            dominated.append(graph_id)

    return {
        "graphs": len(graphs),
        "dominates_fixed": len(dominated),
        "quality_strictly_better": len(quality_better),
        "work_strictly_lower": len(work_lower),
        "dominance_rate": len(dominated) / len(graphs) if graphs else 0.0,
    }


def _curve_quality_at_or_before_budget(
    curve: list[dict],
    budget: int,
) -> int | None:
    candidates = [
        int(point["edge_cut"])
        for point in curve
        if int(point["work"]) <= budget
    ]
    return min(candidates) if candidates else None


def _equal_work_graph_means(
    rows: list[dict],
    policy: str,
) -> dict[str, dict[str, float]]:
    grouped: dict[tuple[str, int], dict[str, dict]] = {}
    for row in rows:
        if row["strategy"] not in {policy, "fixed"}:
            continue
        key = (str(row["graph_id"]), int(row["seed"]))
        grouped.setdefault(key, {})[str(row["strategy"])] = row

    per_graph: dict[str, list[dict[str, float]]] = {}
    for (graph_id, _seed), pair in grouped.items():
        if policy not in pair or "fixed" not in pair:
            continue
        candidate = pair[policy]
        fixed = pair["fixed"]
        budget = min(int(candidate["total_work"]), int(fixed["total_work"]))
        candidate_cut = _curve_quality_at_or_before_budget(
            candidate["work_curve"], budget
        )
        fixed_cut = _curve_quality_at_or_before_budget(
            fixed["work_curve"], budget
        )
        if candidate_cut is None or fixed_cut is None:
            continue
        per_graph.setdefault(graph_id, []).append(
            {
                "candidate": float(candidate_cut),
                "fixed": float(fixed_cut),
                "budget": float(budget),
            }
        )

    return {
        graph_id: {
            "candidate_edge_cut": (
                sum(item["candidate"] for item in values) / len(values)
            ),
            "fixed_edge_cut": (
                sum(item["fixed"] for item in values) / len(values)
            ),
            "common_work_budget": (
                sum(item["budget"] for item in values) / len(values)
            ),
        }
        for graph_id, values in per_graph.items()
        if values
    }


def _equal_work_summary(rows: list[dict], policy: str) -> dict:
    graph_means = _equal_work_graph_means(rows, policy)
    graphs = sorted(graph_means)
    deltas = [
        graph_means[g]["candidate_edge_cut"] - graph_means[g]["fixed_edge_cut"]
        for g in graphs
    ]
    lower, upper = bootstrap_mean_ci(deltas, resamples=20000, seed=2026)
    return {
        "graphs": len(graphs),
        "mean_candidate_edge_cut_at_common_work": (
            sum(graph_means[g]["candidate_edge_cut"] for g in graphs) / len(graphs)
            if graphs else 0.0
        ),
        "mean_fixed_edge_cut_at_common_work": (
            sum(graph_means[g]["fixed_edge_cut"] for g in graphs) / len(graphs)
            if graphs else 0.0
        ),
        "mean_edge_cut_delta_candidate_minus_fixed": (
            sum(deltas) / len(deltas) if deltas else 0.0
        ),
        "bootstrap_95_ci": [lower, upper] if deltas else [0.0, 0.0],
        "candidate_better_graphs": sum(delta < 0 for delta in deltas),
        "fixed_better_graphs": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
        "mean_common_work_budget": (
            sum(graph_means[g]["common_work_budget"] for g in graphs) / len(graphs)
            if graphs else 0.0
        ),
    }


def _corpus_comparison(rows: list[dict], policy: str) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row["corpus"]), []).append(row)

    output: dict[str, dict[str, float | int]] = {}
    for corpus, corpus_rows in sorted(grouped.items()):
        fixed = _graph_policy_means(corpus_rows, "fixed")
        candidate = _graph_policy_means(corpus_rows, policy)
        graphs = sorted(set(fixed) & set(candidate))
        cut_deltas = [
            candidate[g]["edge_cut"] - fixed[g]["edge_cut"]
            for g in graphs
        ]
        work_deltas = [
            candidate[g]["total_work"] - fixed[g]["total_work"]
            for g in graphs
        ]
        dominance = sum(
            candidate[g]["edge_cut"] <= fixed[g]["edge_cut"]
            and candidate[g]["total_work"] <= fixed[g]["total_work"]
            and (
                candidate[g]["edge_cut"] < fixed[g]["edge_cut"]
                or candidate[g]["total_work"] < fixed[g]["total_work"]
            )
            for g in graphs
        )
        output[corpus] = {
            "graphs": len(graphs),
            "mean_edge_cut_delta": (
                sum(cut_deltas) / len(cut_deltas) if cut_deltas else 0.0
            ),
            "mean_total_work_delta": (
                sum(work_deltas) / len(work_deltas) if work_deltas else 0.0
            ),
            "quality_strictly_better": sum(delta < 0 for delta in cut_deltas),
            "work_strictly_lower": sum(delta < 0 for delta in work_deltas),
            "joint_quality_work_dominance_rate": (
                dominance / len(graphs) if graphs else 0.0
            ),
        }
    return output


def run_benchmark(
    output_path: str | Path = "results/state_of_art/dynamic_compute_external.json",
    *,
    cache_dir: str | Path | None = None,
) -> dict:
    started = time.perf_counter()
    corpora, provenance = _load_expanded_corpora(cache_dir=cache_dir)
    rows: list[dict] = []

    graph_count = sum(len(graphs) for graphs in corpora.values())
    if graph_count != 20:
        raise ValueError(f"expected 20 graphs, discovered {graph_count}")

    for corpus, graphs in corpora.items():
        for graph_name, graph in graphs.items():
            graph_id = f"{corpus}/{graph_name}"
            for seed in SEEDS:
                for policy in POLICIES:
                    result = _run_policy(
                        graph,
                        seed=seed,
                        policy=policy,
                    )
                    rows.append(
                        {
                            "corpus": corpus,
                            "graph": graph_name,
                            "graph_id": graph_id,
                            "seed": seed,
                            "strategy": policy,
                            **result,
                        }
                    )

    summaries = {
        policy: _policy_summary(rows, policy)
        for policy in POLICIES
    }

    comparisons = {}
    for policy in ("adaptive", "marginal"):
        comparisons[policy] = {
            "edge_cut_vs_fixed": paired_summary(
                rows,
                strategy_a=policy,
                strategy_b="fixed",
                metric="edge_cut",
                resamples=20000,
                seed=2024,
            ),
            "total_work_vs_fixed": paired_summary(
                rows,
                strategy_a=policy,
                strategy_b="fixed",
                metric="total_work",
                resamples=20000,
                seed=2025,
            ),
            "dominance_vs_fixed": _dominance_vs_fixed(rows, policy),
            "equal_work_vs_fixed": _equal_work_summary(rows, policy),
        }

    payload = {
        "schema_version": "0.1",
        "protocol": (
            "20-graph external dynamic-compute ablation for BLOC-RELOC "
            "with fixed, adaptive, marginal, and no-hybrid controls"
        ),
        "unit_of_analysis": "graph",
        "objective": {
            "name": "unweighted edge cut",
            "direction": "minimize edge cut",
            "balance": "exact floor/ceil balanced bisection",
        },
        "commit_sha": _commit_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "k": 2,
        "seeds": list(SEEDS),
        "iterations": ITERATIONS,
        "hybrid_period": HYBRID_PERIOD,
        "hybrid_samples": HYBRID_SAMPLES,
        "policies": list(POLICIES),
        "corpora": {
            corpus: {
                "graph_count": len(graphs),
                "provenance": provenance[corpus],
            }
            for corpus, graphs in corpora.items()
        },
        "rows": rows,
        "summaries": summaries,
        "comparisons": comparisons,
        "by_corpus": {
            policy: _corpus_comparison(rows, policy)
            for policy in ("adaptive", "marginal")
        },
        "limitations": [
            "This is a BLOC-RELOC controller study, not a comparison against the external multilevel solvers.",
            "Structural work is a machine-independent proxy; wall-clock time remains hardware-specific.",
            "The fixed controller is the primary paired baseline for adaptive and marginal allocation.",
            "Equal-work analysis uses the best recorded edge cut at or before the common per-graph, per-seed structural-work budget.",
            "No public/default routing policy is changed by this experiment.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/dynamic_compute_external.json"),
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run_benchmark(output_path=args.output, cache_dir=args.cache_dir)
    print(json.dumps(result["comparisons"], indent=2))
