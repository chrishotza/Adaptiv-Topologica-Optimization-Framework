import json

import networkx as nx

from atof.benchmark import benchmark_bloc
from experiments.run_canonical import run_suite, spectral_bisection


def test_benchmark_records_are_serializable():
    rows = benchmark_bloc(
        [("cycle", nx.cycle_graph(8))],
        k=2,
        seeds=(42,),
        iterations=2,
    )
    assert len(rows) == 2
    assert {row["variant"] for row in rows} == {"baseline", "affinity"}
    assert all("trace" in row and row["seed"] == 42 for row in rows)


def test_canonical_suite_records_topology(tmp_path):
    output = tmp_path / "benchmark.json"
    payload = run_suite(
        output_path=output,
        k=2,
        seeds=(42,),
        iterations=2,
    )
    assert output.exists()
    assert payload["schema_version"] == "0.2"
    assert len(payload["graphs"]) == 7
    assert payload["rows"]
    row = payload["rows"][0]
    assert "regime" in row
    assert "degree_gini" in row
    assert "modularity" in row
    assert json.loads(output.read_text(encoding="utf-8"))["rows"]


def test_spectral_bisection_is_balanced_and_serializable():
    graph = nx.path_graph(9)
    result = spectral_bisection(graph)
    assert result["edge_cut"] >= 0
    assert result["balance_error"] == 0.0
    assert result["weighted_cost"] == float(result["edge_cut"])
