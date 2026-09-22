import pytest
from pathlib import Path
import json

import networkx as nx

from atof.product import load_graph, optimize_graph


def test_optimize_graph_supports_kway_engine():
    graph = nx.cycle_graph(12)
    result = optimize_graph(graph, k=4, seed=42, iterations=4, variant="baseline")

    counts = [list(result.partition_result.partition.values()).count(block) for block in range(4)]

    assert result.k == 4
    assert sorted(counts) == [3, 3, 3, 3]
    assert result.partition_result.balance_error == 0.0
    assert set(result.partition_result.partition.values()) == {0, 1, 2, 3}


def test_optimize_graph_returns_balanced_product_result():
    graph = nx.path_graph(8)
    result = optimize_graph(graph, k=2, seed=42, iterations=3, variant="baseline")

    payload = result.to_dict()
    assert result.selected_variant == "baseline"
    assert payload["result"]["k"] == 2
    assert payload["result"]["balance_error"] == 0.0
    assert len(payload["result"]["partition"]) == 8
    assert payload["parameters"]["seed"] == 42
    assert payload["provenance"]["graph_fingerprint"]


def test_load_graph_supports_json(tmp_path: Path):
    path = tmp_path / "graph.json"
    path.write_text(
        '{"nodes": ["a", "b", "isolated"], "edges": [["a", "b"]]}',
        encoding="utf-8",
    )

    loaded = load_graph(path)
    assert loaded.number_of_nodes() == 3
    assert loaded.number_of_edges() == 1


def test_load_graph_from_json_stdin(monkeypatch):
    import io
    import sys

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO('{"nodes": ["a", "b"], "edges": [["a", "b"]]}'),
    )
    loaded = load_graph("-", format="json")

    assert loaded.number_of_nodes() == 2
    assert loaded.number_of_edges() == 1


def test_load_graph_rejects_invalid_json_graph(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text('{"edges": [["a"]]}', encoding="utf-8")

    with pytest.raises(ValueError, match="2-item arrays"):
        load_graph(path)


def test_load_graph_supports_graphml(tmp_path: Path):
    graph = nx.path_graph(5)
    path = tmp_path / "graph.graphml"
    nx.write_graphml(graph, path)

    loaded = load_graph(path)
    assert loaded.number_of_nodes() == 5
    assert loaded.number_of_edges() == 4


def test_load_graph_from_stdin(monkeypatch):
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("a b\nb c\nc d\n"))
    loaded = load_graph("-")

    assert loaded.number_of_nodes() == 4
    assert loaded.number_of_edges() == 3


def test_load_graph_rejects_non_edgelist_stdin():
    with pytest.raises(ValueError, match="edge-list"):
        load_graph("-", format="graphml")


def test_load_graph_rejects_unknown_format(tmp_path: Path):
    path = tmp_path / "graph.data"
    path.write_text("0 1\n", encoding="utf-8")

    try:
        load_graph(path, format="unknown")
    except ValueError as exc:
        assert "format must be one of" in str(exc)
    else:
        raise AssertionError("unknown format should fail")

def test_write_partition_exports_csv_json_and_tsv(tmp_path):
    from atof.product import write_partition

    graph = nx.path_graph(6)
    result = optimize_graph(graph, k=2, seed=42, iterations=2, variant="baseline")

    csv_path = write_partition(result, tmp_path / "partition.csv")
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "node,block"
    assert len(csv_path.read_text(encoding="utf-8").splitlines()) == 7

    json_path = write_partition(result, tmp_path / "partition.json")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload) == 6
    assert set(payload[0]) == {"node", "block"}

    tsv_path = write_partition(result, tmp_path / "partition.tsv")
    assert tsv_path.read_text(encoding="utf-8").splitlines()[0] == "node\tblock"


def test_write_partition_mapping_supports_generic_portfolio_mapping(tmp_path):
    from atof.product import write_partition_mapping

    output = write_partition_mapping(
        {"a": 1, "b": 0},
        tmp_path / "portfolio.json",
        format="json",
    )
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == [
        {"node": "b", "block": 0},
        {"node": "a", "block": 1},
    ]

def test_optimize_graph_rejects_unsupported_graph_models():
    import pytest

    directed = nx.DiGraph([(0, 1), (1, 2)])
    with pytest.raises(ValueError, match="undirected"):
        optimize_graph(directed)

    multigraph = nx.MultiGraph([(0, 1), (0, 1)])
    with pytest.raises(ValueError, match="simple graph"):
        optimize_graph(multigraph)

    weighted = nx.Graph()
    weighted.add_edge("a", "b", weight=2.0)
    weighted_result = optimize_graph(weighted)
    assert weighted_result.partition_result.edge_cut == 1


def test_optimize_graph_rejects_invalid_iterations():
    with pytest.raises(ValueError, match="iterations"):
        optimize_graph(nx.path_graph(4), iterations=0)
