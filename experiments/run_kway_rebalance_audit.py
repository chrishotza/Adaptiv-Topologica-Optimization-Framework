from __future__ import annotations

import argparse
import json
import subprocess
import sys
import statistics
from collections import Counter
from pathlib import Path

import networkx as nx

from atof.partition import edge_cut, rebalance_kway, exact_balanced_block_weights
from experiments.run_expanded_20graph_kahip_transfer import _load_expanded_corpora

SEEDS = (42, 101, 2024)
K_VALUES = (4, 8, 32, 64)
STRATEGIES = ("metis", "kahip")


def _raw_metis(graph: nx.Graph, seed: int, k: int) -> list[int]:
    import pymetis

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = [
        [index[neighbor] for neighbor in graph.neighbors(node)]
        for node in nodes
    ]
    result = pymetis.part_graph(
        k,
        adjacency=adjacency,
        tpwgts=[1.0 / k] * k,
        recursive=True,
        options=pymetis.Options(seed=seed),
    )
    return [int(block) for block in result.vertex_part]


def _raw_kahip(graph: nx.Graph, seed: int, k: int) -> list[int]:
    import kahip

    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}
    xadj = [0]
    adjncy: list[int] = []
    for node in nodes:
        adjncy.extend(index[neighbor] for neighbor in graph.neighbors(node))
        xadj.append(len(adjncy))

    _, membership = kahip.kaffpa(
        [1] * len(nodes),
        xadj,
        [1] * len(adjncy),
        adjncy,
        k,
        0.0,
        1,
        int(seed),
        2,
    )
    return [int(block) for block in membership]


def _raw_runner(strategy: str):
    if strategy == "metis":
        return _raw_metis
    if strategy == "kahip":
        return _raw_kahip
    raise ValueError(f"unknown strategy: {strategy}")


def _partition_from_membership(
    graph: nx.Graph,
    membership: list[int],
) -> dict:
    return {
        node: int(block)
        for node, block in zip(graph.nodes(), membership)
    }


def _counts(membership: list[int], k: int) -> list[int]:
    counts = [0] * k
    for block in membership:
        if block < 0 or block >= k:
            raise ValueError("membership contains an invalid block label")
        counts[block] += 1
    return counts


def audit_membership(
    graph: nx.Graph,
    membership: list[int],
    k: int,
) -> dict:
    if len(membership) != graph.number_of_nodes():
        raise ValueError("membership length must match graph node count")

    raw_partition = _partition_from_membership(graph, membership)
    raw_counts = _counts(membership, k)
    repaired = rebalance_kway(graph, list(membership), k)
    repaired_partition = _partition_from_membership(graph, repaired)
    repaired_counts = _counts(repaired, k)

    expected = sorted(exact_balanced_block_weights(graph.number_of_nodes(), k))
    if sorted(repaired_counts) != expected:
        raise ValueError(
            f"repair violated exact balance contract: counts={repaired_counts}, "
            f"expected={expected}"
        )

    changed = sum(
        old != new for old, new in zip(membership, repaired)
    )
    raw_cut = edge_cut(graph, raw_partition)
    repaired_cut = edge_cut(graph, repaired_partition)

    return {
        "raw_edge_cut": int(raw_cut),
        "repaired_edge_cut": int(repaired_cut),
        "cut_delta": int(repaired_cut - raw_cut),
        "cut_delta_percent": (
            100.0 * (repaired_cut - raw_cut) / raw_cut
            if raw_cut
            else 0.0
        ),
        "repair_moves": int(changed),
        "raw_block_counts": raw_counts,
        "repaired_block_counts": repaired_counts,
        "repair_needed": bool(changed),
        "raw_within_exact_contract": sorted(raw_counts) == expected,
    }


def _audit_strategy(
    strategy: str,
    cache_dir: str | None,
    k_values: tuple[int, ...],
) -> list[dict]:
    corpora, _ = _load_expanded_corpora(
        cache_dir=Path(cache_dir) if cache_dir else None
    )
    runner = _raw_runner(strategy)
    rows: list[dict] = []

    for k in k_values:
        for corpus, graphs in corpora.items():
            for graph_name, graph in graphs.items():
                graph_id = f"{corpus}/{graph_name}"
                for seed in SEEDS:
                    row = {
                        "strategy": strategy,
                        "k": k,
                        "corpus": corpus,
                        "graph": graph_name,
                        "graph_id": graph_id,
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                        "seed": seed,
                    }
                    if graph.number_of_nodes() < k:
                        row.update({
                            "status": "skipped",
                            "error": "k exceeds graph node count",
                        })
                        rows.append(row)
                        continue

                    try:
                        membership = runner(graph, seed, k)
                        row.update(audit_membership(graph, membership, k))
                        row["status"] = "ok"
                    except Exception as exc:
                        row.update({
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                    rows.append(row)

    return rows


def _summarize(rows: list[dict]) -> dict:
    ok = [row for row in rows if row.get("status") == "ok"]
    by_key: dict[tuple[int, str], list[dict]] = {}
    for row in ok:
        by_key.setdefault((int(row["k"]), str(row["strategy"])), []).append(row)

    summary = {}
    for (k, strategy), group in sorted(by_key.items()):
        deltas = [float(row["cut_delta"]) for row in group]
        delta_pct = [float(row["cut_delta_percent"]) for row in group]
        moves = [int(row["repair_moves"]) for row in group]
        summary[f"k={k}:{strategy}"] = {
            "rows": len(group),
            "repair_required_rows": sum(row["repair_needed"] for row in group),
            "repair_required_fraction": (
                sum(row["repair_needed"] for row in group) / len(group)
            ),
            "mean_cut_delta": statistics.fmean(deltas) if deltas else 0.0,
            "max_cut_delta": max(deltas, default=0.0),
            "mean_cut_delta_percent": statistics.fmean(delta_pct) if delta_pct else 0.0,
            "max_cut_delta_percent": max(delta_pct, default=0.0),
            "mean_repair_moves": statistics.fmean(moves) if moves else 0.0,
            "raw_exact_balance_fraction": (
                sum(row["raw_within_exact_contract"] for row in group) / len(group)
            ),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=STRATEGIES)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument(
        "--k",
        type=int,
        choices=K_VALUES,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/kway_rebalance_audit.json"),
    )
    args = parser.parse_args()

    k_values = tuple(args.k) if args.k else K_VALUES

    if args.worker:
        if args.strategy is None:
            raise SystemExit("--strategy is required with --worker")
        rows = _audit_strategy(
            args.strategy,
            str(args.cache_dir) if args.cache_dir else None,
            k_values,
        )
        print(json.dumps(rows))
        return 0

    strategies = (args.strategy,) if args.strategy else STRATEGIES
    all_rows: list[dict] = []

    for strategy in strategies:
        command = [
            sys.executable,
            "-m",
            "experiments.run_kway_rebalance_audit",
            "--worker",
            "--strategy",
            strategy,
        ]
        for k in k_values:
            command.extend(["--k", str(k)])
        if args.cache_dir is not None:
            command.extend(["--cache-dir", str(args.cache_dir)])

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
        )
        if completed.returncode != 0:
            all_rows.append({
                "strategy": strategy,
                "status": "error",
                "error": (
                    f"isolated worker exit {completed.returncode}: "
                    f"{completed.stderr[-2000:]}"
                ),
            })
            continue

        try:
            payload = json.loads(
                [line for line in completed.stdout.splitlines() if line.strip()][-1]
            )
        except (json.JSONDecodeError, IndexError) as exc:
            all_rows.append({
                "strategy": strategy,
                "status": "error",
                "error": f"invalid worker JSON: {type(exc).__name__}: {exc}",
            })
            continue

        all_rows.extend(payload)

    output = {
        "schema_version": "0.1",
        "protocol": "K-way raw-vs-rebalanced external backend audit",
        "strategies": list(strategies),
        "k_values": list(k_values),
        "seeds": list(SEEDS),
        "rows": all_rows,
        "summary": _summarize(all_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(output["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
