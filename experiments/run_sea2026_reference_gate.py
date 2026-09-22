from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx

SEA_REVISION = "6d12d9cf210390624f3757e9b5399469d2d2ae68"
SEA_VERSION = "1.5.3"
SEA_ZENODO_RECORD = "https://zenodo.org/records/19387774"
DEFAULT_SEEDS = (1, 2, 3, 4, 5)
DEFAULT_K_VALUES = (4, 8, 32, 64)
DEFAULT_EPSILON = 0.03


def read_metis_graph(path: Path) -> nx.Graph:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    raw = [line.rstrip() for line in lines if not line.lstrip().startswith("%")]
    while raw and not raw[0].strip():
        raw.pop(0)
    if not raw:
        raise ValueError("empty METIS file")

    header = raw[0].split()
    if len(header) < 2:
        raise ValueError("METIS header must contain node and edge counts")

    node_count = int(header[0])
    edge_count = int(header[1])
    if len(raw) != node_count + 1:
        raise ValueError(
            f"expected {node_count} adjacency lines, found {len(raw) - 1}"
        )

    graph = nx.Graph()
    graph.add_nodes_from(range(1, node_count + 1))
    for node_id, line in enumerate(raw[1:], start=1):
        for token in line.split():
            neighbor = int(token)
            if neighbor < 1 or neighbor > node_count:
                raise ValueError(f"neighbor {neighbor} out of range")
            if neighbor != node_id:
                graph.add_edge(node_id, neighbor)

    if graph.number_of_edges() != edge_count:
        raise ValueError(
            f"header edge count {edge_count} != parsed edge count "
            f"{graph.number_of_edges()}"
        )
    return graph


def discover_graph_files(root: Path) -> list[Path]:
    paths = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            read_metis_graph(path)
        except (OSError, UnicodeError, ValueError):
            continue
        paths.append(path)
    return sorted(paths)


def partition_file_for(
    output_dir: Path,
    graph_file: Path,
    k: int,
    epsilon: float,
    seed: int,
) -> Path:
    epsilon_text = f"{epsilon:g}"
    return (
        output_dir
        / f"{graph_file.name}.part{k}.epsilon{epsilon_text}.seed{seed}.KaHyPar"
    )


def parse_partition(
    path: Path,
    node_count: int,
    k: int | None = None,
) -> list[int]:
    values = [
        int(token)
        for token in path.read_text(encoding="utf-8").split()
    ]
    if len(values) != node_count:
        raise ValueError(
            f"partition length {len(values)} != node count {node_count}"
        )
    if any(block < 0 for block in values):
        raise ValueError("partition contains negative block id")
    if k is not None and any(block >= k for block in values):
        raise ValueError(
            f"partition contains block id outside [0, {k})"
        )
    return values


def edge_cut(graph: nx.Graph, partition: list[int]) -> int:
    return sum(partition[u - 1] != partition[v - 1] for u, v in graph.edges())


def block_counts(partition: list[int], k: int) -> list[int]:
    return [partition.count(block) for block in range(k)]


def balance_bound_ok(
    graph: nx.Graph,
    counts: list[int],
    k: int,
    epsilon: float,
) -> bool:
    if len(counts) != k:
        return False
    bound = (1.0 + epsilon) * ((graph.number_of_nodes() + k - 1) // k)
    return max(counts, default=0) <= bound + 1e-12


def run_configuration(
    binary: Path,
    graph_file: Path,
    output_dir: Path,
    *,
    k: int,
    seed: int,
    threads: int,
    epsilon: float,
    learned: bool,
) -> dict:
    graph = read_metis_graph(graph_file)
    output_dir.mkdir(parents=True, exist_ok=True)
    partition_path = partition_file_for(
        output_dir, graph_file, k, epsilon, seed
    )
    if partition_path.exists():
        partition_path.unlink()

    command = [
        str(binary),
        "-h",
        str(graph_file),
        "--instance-type=graph",
        "--input-file-format=metis",
        "--preset=default",
        "-o",
        "cut",
        "-k",
        str(k),
        "-e",
        str(epsilon),
        "-t",
        str(threads),
        "--seed=" + str(seed),
        "--verbose=false",
        "--write-partition-file=true",
        "--partition-output-folder=" + str(output_dir),
    ]
    if not learned:
        command.extend(
            [
                "--c-guiding-by-integrated-model=false",
            ]
        )

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    runtime = time.perf_counter() - started

    if completed.returncode != 0:
        raise RuntimeError(
            f"Mt-KaHyPar exit {completed.returncode}: "
            f"{completed.stderr[-2000:]}"
        )

    if not partition_path.exists():
        candidates = sorted(
            output_dir.glob(
                f"{graph_file.name}.part{k}.epsilon*.seed{seed}.KaHyPar"
            )
        )
        if len(candidates) != 1:
            raise FileNotFoundError(
                f"expected one partition file for {graph_file.name}, "
                f"found {[p.name for p in candidates]}"
            )
        partition_path = candidates[0]

    partition = parse_partition(partition_path, graph.number_of_nodes(), k)
    counts = block_counts(partition, k)
    balance_ok = balance_bound_ok(graph, counts, k, epsilon)
    if not balance_ok:
        raise ValueError(
            "partition violates SEA epsilon balance bound"
            f"; counts={counts}; k={k}; epsilon={epsilon}"
        )
    return {
        "status": "ok",
        "edge_cut": edge_cut(graph, partition),
        "balance_ok": True,
        "block_counts": counts,
        "runtime_seconds": runtime,
        "command": command,
        "partition_file": str(partition_path),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def run_reference_gate(
    binary: Path,
    set_a_dir: Path,
    output_path: Path,
    *,
    limit: int,
    seeds: tuple[int, ...],
    k_values: tuple[int, ...],
    threads: int,
    epsilon: float,
) -> dict:
    graph_files = discover_graph_files(set_a_dir)
    if limit < 0 and len(graph_files) != 118:
        raise ValueError(
            f"expected 118 Set A graph files, discovered {len(graph_files)}"
        )
    selected = graph_files if limit < 0 else graph_files[:limit]
    rows: list[dict] = []
    started = time.perf_counter()

    for graph_file in selected:
        graph = read_metis_graph(graph_file)
        graph_id = str(graph_file.relative_to(set_a_dir)).replace("\\", "/")
        for seed in seeds:
            for k in k_values:
                if graph.number_of_nodes() < k:
                    rows.append({
                        "graph_id": graph_id,
                        "seed": seed,
                        "k": k,
                        "status": "skipped",
                        "error": "k exceeds node count",
                    })
                    continue

                for learned, label in (
                    (True, "learned"),
                    (False, "baseline"),
                ):
                    row = {
                        "graph_id": graph_id,
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                        "seed": seed,
                        "k": k,
                        "configuration": label,
                    }
                    case_dir = (
                        output_path.parent / "sea_reference_runs" / label
                    )
                    try:
                        row.update(
                            run_configuration(
                                binary,
                                graph_file,
                                case_dir,
                                k=k,
                                seed=seed,
                                threads=threads,
                                epsilon=epsilon,
                                learned=learned,
                            )
                        )
                    except Exception as exc:
                        row.update({
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                    rows.append(row)

    valid = [
        row for row in rows
        if row.get("status") == "ok" and row.get("balance_ok")
    ]
    paired: list[dict] = []
    index = {
        (
            row["graph_id"],
            row["seed"],
            row["k"],
            row["configuration"],
        ): row
        for row in valid
    }
    for graph_id in sorted({row["graph_id"] for row in valid}):
        for seed in seeds:
            for k in k_values:
                learned = index.get((graph_id, seed, k, "learned"))
                baseline = index.get((graph_id, seed, k, "baseline"))
                if learned and baseline:
                    paired.append({
                        "graph_id": graph_id,
                        "seed": seed,
                        "k": k,
                        "learned_edge_cut": learned["edge_cut"],
                        "baseline_edge_cut": baseline["edge_cut"],
                        "relative_cut_delta": (
                            (
                                learned["edge_cut"] - baseline["edge_cut"]
                            )
                            / baseline["edge_cut"]
                            if baseline["edge_cut"]
                            else None
                        ),
                        "learned_runtime_seconds": (
                            learned["runtime_seconds"]
                        ),
                        "baseline_runtime_seconds": (
                            baseline["runtime_seconds"]
                        ),
                    })

    deltas = [
        row["relative_cut_delta"]
        for row in paired
        if row["relative_cut_delta"] is not None
    ]
    learned_runtime = [
        row["learned_runtime_seconds"] for row in paired
    ]
    baseline_runtime = [
        row["baseline_runtime_seconds"] for row in paired
    ]

    # Match the paper-style aggregation hierarchy: arithmetic mean across
    # seeds for each graph×k instance, then geometric mean across instances.
    instance_groups: dict[tuple[str, int, str], list[dict]] = {}
    for row in valid:
        key = (row["graph_id"], int(row["k"]), row["configuration"])
        instance_groups.setdefault(key, []).append(row)

    instance_summaries: dict[tuple[str, int], dict[str, dict]] = {}
    for key, group in instance_groups.items():
        graph_id, k, configuration = key
        instance_summaries.setdefault((graph_id, k), {})[configuration] = {
            "seed_count": len(group),
            "edge_cut_mean": statistics.fmean(
                float(row["edge_cut"]) for row in group
            ),
            "runtime_mean_seconds": statistics.fmean(
                float(row["runtime_seconds"]) for row in group
            ),
        }

    protocol_pairs: list[dict] = []
    protocol_incomplete_instances: list[dict] = []
    for (graph_id, k), configurations in sorted(instance_summaries.items()):
        learned_instance = configurations.get("learned")
        baseline_instance = configurations.get("baseline")
        if learned_instance is None or baseline_instance is None:
            continue

        seed_count_learned = learned_instance["seed_count"]
        seed_count_baseline = baseline_instance["seed_count"]
        if (
            seed_count_learned != len(seeds)
            or seed_count_baseline != len(seeds)
        ):
            protocol_incomplete_instances.append({
                "graph_id": graph_id,
                "k": k,
                "seed_count_learned": seed_count_learned,
                "seed_count_baseline": seed_count_baseline,
                "required_seed_count": len(seeds),
            })
            continue

        baseline_cut = baseline_instance["edge_cut_mean"]
        protocol_pairs.append({
            "graph_id": graph_id,
            "k": k,
            "seed_count_learned": seed_count_learned,
            "seed_count_baseline": seed_count_baseline,
            "learned_edge_cut_mean": learned_instance["edge_cut_mean"],
            "baseline_edge_cut_mean": baseline_cut,
            "relative_cut_delta": (
                (learned_instance["edge_cut_mean"] - baseline_cut) / baseline_cut
                if baseline_cut
                else None
            ),
            "learned_runtime_mean_seconds": learned_instance[
                "runtime_mean_seconds"
            ],
            "baseline_runtime_mean_seconds": baseline_instance[
                "runtime_mean_seconds"
            ],
        })

    protocol_deltas = [
        row["relative_cut_delta"]
        for row in protocol_pairs
        if row["relative_cut_delta"] is not None
    ]
    protocol_cut_ratios = [1.0 + delta for delta in protocol_deltas]
    protocol_learned_runtime = [
        row["learned_runtime_mean_seconds"] for row in protocol_pairs
    ]
    protocol_baseline_runtime = [
        row["baseline_runtime_mean_seconds"] for row in protocol_pairs
    ]
    protocol_learned_runtime_ratios = [
        row["learned_runtime_mean_seconds"] / row["baseline_runtime_mean_seconds"]
        for row in protocol_pairs
        if row["baseline_runtime_mean_seconds"] > 0
    ]

    return {
        "schema_version": "0.2",
        "protocol": "SEA 2026 exact-software reference gate",
        "source": {
            "paper_artifact_version": SEA_VERSION,
            "git_revision": SEA_REVISION,
            "zenodo_record": SEA_ZENODO_RECORD,
        },
        "contract": {
            "objective": "unweighted edge cut",
            "epsilon": epsilon,
            "k_values": list(k_values),
            "seeds": list(seeds),
            "threads_requested": threads,
            "threads_are_environment_limited": True,
            "learned_configuration": "default snapshot configuration",
            "baseline_configuration": (
                "default preset with the integrated model disabled; "
                "all other default preset options remain unchanged"
            ),
            "baseline_overrides": [
                "--c-guiding-by-integrated-model=false",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "binary": str(binary),
        },
        "discovered_graphs": len(graph_files),
        "selected_graphs": len(selected),
        "rows": rows,
        "paired_rows": paired,
        "instance_summaries": [
            {
                "graph_id": graph_id,
                "k": k,
                **summary_by_configuration,
            }
            for (graph_id, k), summary_by_configuration
            in sorted(instance_summaries.items())
        ],
        "protocol_pairs": protocol_pairs,
        "protocol_incomplete_instances": protocol_incomplete_instances,
        "summary": {
            "total_rows": len(rows),
            "ok_rows": sum(row.get("status") == "ok" for row in rows),
            "error_rows": sum(row.get("status") == "error" for row in rows),
            "skipped_rows": sum(row.get("status") == "skipped" for row in rows),
            "paired_rows": len(paired),
            "mean_relative_cut_delta": (
                statistics.fmean(deltas) if deltas else None
            ),
            "geometric_mean_cut_ratio": (
                statistics.geometric_mean(
                    [1.0 + delta for delta in deltas]
                )
                if deltas else None
            ),
            "mean_learned_runtime_seconds": (
                statistics.fmean(learned_runtime)
                if learned_runtime else None
            ),
            "mean_baseline_runtime_seconds": (
                statistics.fmean(baseline_runtime)
                if baseline_runtime else None
            ),
            "protocol_instances": len(protocol_pairs),
            "protocol_incomplete_instances": len(protocol_incomplete_instances),
            "protocol_mean_relative_cut_delta": (
                statistics.fmean(protocol_deltas)
                if protocol_deltas else None
            ),
            "protocol_geometric_mean_cut_ratio": (
                statistics.geometric_mean(protocol_cut_ratios)
                if protocol_cut_ratios else None
            ),
            "protocol_geometric_mean_cut_gap_percent": (
                100.0 * (
                    statistics.geometric_mean(protocol_cut_ratios) - 1.0
                )
                if protocol_cut_ratios else None
            ),
            "protocol_mean_learned_runtime_seconds": (
                statistics.fmean(protocol_learned_runtime)
                if protocol_learned_runtime else None
            ),
            "protocol_mean_baseline_runtime_seconds": (
                statistics.fmean(protocol_baseline_runtime)
                if protocol_baseline_runtime else None
            ),
            "protocol_geometric_mean_runtime_ratio": (
                statistics.geometric_mean(protocol_learned_runtime_ratios)
                if protocol_learned_runtime_ratios else None
            ),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--set-a-dir", type=Path, required=True)
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Number of Set A graphs; use -1 for all graphs.",
    )
    parser.add_argument("--seed", type=int, action="append", dest="seeds")
    parser.add_argument("--k", type=int, action="append", dest="k_values")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/sea2026_reference_gate.json"),
    )
    args = parser.parse_args()

    if args.limit == 0:
        raise SystemExit("--limit must be non-zero")
    if not args.binary.exists():
        raise SystemExit(
            f"Mt-KaHyPar binary not found: {args.binary}"
        )
    if not args.set_a_dir.exists():
        raise SystemExit(f"Set A directory not found: {args.set_a_dir}")

    payload = run_reference_gate(
        args.binary,
        args.set_a_dir,
        args.output,
        limit=args.limit,
        seeds=tuple(args.seeds or DEFAULT_SEEDS),
        k_values=tuple(args.k_values or DEFAULT_K_VALUES),
        threads=args.threads,
        epsilon=args.epsilon,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
