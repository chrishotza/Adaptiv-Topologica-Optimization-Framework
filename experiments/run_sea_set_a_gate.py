from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import networkx as nx

from atof.portfolio import optimize_portfolio

SEA_ZENODO_RECORD = "https://zenodo.org/records/19387774"
SEA_SET_A_MD5 = "94606409c10bced915890cf6e6fda213"
EXPECTED_GRAPHS = 118
DEFAULT_SEEDS = (42, 101, 2024)
DEFAULT_K_VALUES = (4, 8, 32, 64)


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_graph_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


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


def corpus_manifest(root: Path) -> dict:
    entries = []
    for path in discover_graph_files(root):
        try:
            graph = read_metis_graph(path)
        except (OSError, ValueError, UnicodeError):
            continue
        entries.append(
            {
                "file": str(path.relative_to(root)).replace("\\", "/"),
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    return {
        "root": str(root),
        "graph_files_detected": len(entries),
        "graphs": entries,
    }


def select_graphs(root: Path, limit: int | None) -> list[tuple[str, nx.Graph]]:
    candidates = []
    for path in discover_graph_files(root):
        try:
            graph = read_metis_graph(path)
        except (OSError, ValueError, UnicodeError):
            continue
        candidates.append(
            (str(path.relative_to(root)).replace("\\", "/"), graph)
        )
    return candidates if limit is None else candidates[:limit]


def run_quality_gate(
    root: Path,
    *,
    limit: int | None,
    seeds: tuple[int, ...],
    k_values: tuple[int, ...],
) -> dict:
    selected = select_graphs(root, limit)
    rows: list[dict] = []
    started = time.perf_counter()

    for file_name, graph in selected:
        graph_id = f"sea2026/set_a/{file_name}"
        for seed in seeds:
            for k in k_values:
                row = {
                    "graph_id": graph_id,
                    "file": file_name,
                    "nodes": graph.number_of_nodes(),
                    "edges": graph.number_of_edges(),
                    "seed": seed,
                    "k": k,
                }

                if graph.number_of_nodes() < k:
                    row.update(
                        {"status": "skipped", "error": "k exceeds node count"}
                    )
                    rows.append(row)
                    continue

                try:
                    result = optimize_portfolio(
                        graph,
                        k=k,
                        seed=seed,
                        iterations=25,
                        include_optional=True,
                    )
                    payload = result.to_dict(include_partition=False)
                    row.update(
                        {
                            "status": "ok",
                            "selected_strategy": result.selected_strategy,
                            "selected_edge_cut": result.selected_edge_cut,
                            "selected_balance_error": result.selected_balance_error,
                            "candidates": payload["candidates"],
                        }
                    )
                except Exception as exc:
                    row.update(
                        {
                            "status": "error",
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                rows.append(row)

    ok = [row for row in rows if row["status"] == "ok"]
    selected_cuts = [float(row["selected_edge_cut"]) for row in ok]

    return {
        "schema_version": "0.1",
        "protocol": "ATOF Set A controlled quality gate",
        "note": (
            "This gate validates the SEA 2026 Set A corpus and exercises ATOF's "
            "common portfolio contract. It is not a direct numerical reproduction "
            "of the SEA paper because the paper uses a different hardware/thread "
            "configuration, epsilon=0.03, five randomized runs, and published "
            "solver-specific timing protocols."
        ),
        "source": {
            "record": SEA_ZENODO_RECORD,
            "set": "Set A",
            "expected_graphs": EXPECTED_GRAPHS,
            "expected_md5": SEA_SET_A_MD5,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "selected_graphs": len(selected),
        "seeds": list(seeds),
        "k_values": list(k_values),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "ok": len(ok),
            "errors": sum(row["status"] == "error" for row in rows),
            "skipped": sum(row["status"] == "skipped" for row in rows),
            "selected_edge_cut_mean": (
                statistics.fmean(selected_cuts) if selected_cuts else None
            ),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set-a-dir", type=Path, required=True)
    parser.add_argument("--set-a-zip", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/state_of_art/set_a_gate.json"),
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--seed", type=int, action="append", dest="seeds")
    parser.add_argument("--k", type=int, action="append", dest="k_values")
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()

    root = args.set_a_dir
    if not root.exists():
        raise SystemExit(f"Set A directory does not exist: {root}")

    if args.set_a_zip:
        observed = md5_file(args.set_a_zip)
        if observed != SEA_SET_A_MD5:
            raise SystemExit(
                f"Set A MD5 mismatch: expected {SEA_SET_A_MD5}, observed {observed}"
            )

    manifest = corpus_manifest(root)
    if manifest["graph_files_detected"] != EXPECTED_GRAPHS:
        raise SystemExit(
            f"Expected {EXPECTED_GRAPHS} METIS graphs, found "
            f"{manifest['graph_files_detected']}"
        )

    payload = {
        "schema_version": "0.1",
        "protocol": "ATOF Set A corpus manifest",
        "source": {
            "record": SEA_ZENODO_RECORD,
            "set": "Set A",
            "expected_graphs": EXPECTED_GRAPHS,
            "expected_md5": SEA_SET_A_MD5,
        },
        "manifest": manifest,
    }

    if not args.manifest_only:
        payload["quality_gate"] = run_quality_gate(
            root,
            limit=args.limit,
            seeds=tuple(args.seeds or DEFAULT_SEEDS),
            k_values=tuple(args.k_values or DEFAULT_K_VALUES),
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload.get("quality_gate", payload["manifest"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
