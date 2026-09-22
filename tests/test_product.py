from pathlib import Path
import json

import networkx as nx

from atof.product import load_graph, optimize_graph


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


def test_load_graph_supports_graphml(tmp_path: Path):
    graph = nx.path_graph(5)
    path = tmp_path / "graph.graphml"
    nx.write_graphml(graph, path)

    loaded = load_graph(path)
    assert loaded.number_of_nodes() == 5
    assert loaded.number_of_edges() == 4


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
