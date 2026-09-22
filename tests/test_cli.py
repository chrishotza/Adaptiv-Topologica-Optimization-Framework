import io
import json

from atof.cli import main


def test_cli_profile(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text("0 1\n1 2\n2 3\n", encoding="utf-8")

    assert main(["profile", str(graph)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["nodes"] == 4
    assert payload["edges"] == 3
    assert "topology" in payload
    assert "recommendation" in payload


def test_cli_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.6.0"


def test_cli_solve_json_file(tmp_path, capsys):
    graph = tmp_path / "graph.json"
    graph.write_text(
        '{"nodes": ["a", "b", "c", "isolated"], "edges": [["a", "b"], ["b", "c"]]}',
        encoding="utf-8",
    )

    assert main(["solve", str(graph)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "portfolio"
    assert payload["graph"] == {"nodes": 4, "edges": 2}


def test_cli_solve_json_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"nodes": ["a", "b", "c"], "edges": [["a", "b"], ["b", "c"]]}'),
    )

    assert main(["solve", "-", "--format", "json", "--iterations", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "portfolio"
    assert payload["graph"] == {"nodes": 3, "edges": 2}


def test_cli_solve_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("0 1\n1 2\n2 3\n3 0\n"),
    )

    assert main(["solve", "-", "--iterations", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "portfolio"
    assert payload["graph"] == {"nodes": 4, "edges": 4}
    assert payload["result"]["k"] == 2


def test_cli_solve_emits_compact_portfolio_result(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text("0 1\n1 2\n2 3\n3 0\n", encoding="utf-8")

    assert main(["solve", str(graph)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "portfolio"
    assert payload["graph"] == {"nodes": 4, "edges": 4}
    assert payload["result"]["k"] == 2
    assert payload["provenance"]["graph_fingerprint"]


def test_cli_solve_exports_partition(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text("a b\nb c\nc d\n", encoding="utf-8")
    output = tmp_path / "partition.csv"

    assert main([
        "solve",
        str(graph),
        "--partition-output",
        str(output),
    ]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "portfolio"
    assert output.read_text(encoding="utf-8").splitlines()[0] == "node,block"
    assert len(output.read_text(encoding="utf-8").splitlines()) == 5

def test_cli_optimize_supports_kway_engine(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text(
        "0 1\n1 2\n2 3\n3 4\n4 5\n5 6\n6 7\n7 0\n8 9\n9 10\n10 11\n11 8\n",
        encoding="utf-8",
    )

    assert main([
        "optimize",
        str(graph),
        "--engine",
        "bloc",
        "--k",
        "4",
        "--iterations",
        "3",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["result"]["k"] == 4
    assert payload["result"]["balance_error"] == 0.0
    assert set(payload["result"]["partition"].values()) == {0, 1, 2, 3}


def test_cli_optimize(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text("0 1\n1 2\n2 3\n3 4\n4 5\n", encoding="utf-8")

    assert main(["optimize", str(graph), "--k", "2", "--iterations", "3"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "optimize"
    assert payload["strategy"]["requested"] == "auto"
    assert payload["strategy"]["selected"].startswith("BLOCReloc(")
    assert payload["result"]["k"] == 2
    assert payload["result"]["balance_error"] == 0.0
    assert len(payload["result"]["partition"]) == 6


def test_cli_optimize_writes_json(tmp_path, capsys):
    graph = tmp_path / "graph.edgelist"
    graph.write_text("0 1\n1 2\n2 3\n", encoding="utf-8")
    output = tmp_path / "result.json"

    assert main([
        "optimize",
        str(graph),
        "--variant",
        "baseline",
        "--output",
        str(output),
    ]) == 0

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["strategy"]["selected"] == "BLOCReloc(baseline)"
    assert capsys.readouterr().out.strip() == str(output)
def test_cli_returns_structured_error_for_malformed_graphml(tmp_path, capsys):
    graph = tmp_path / "broken.graphml"
    graph.write_text("<graphml>", encoding="utf-8")

    code = main(["solve", str(graph), "--format", "graphml"])
    parsed = json.loads(capsys.readouterr().out)

    assert code == 2
    assert parsed["schema"] == "atof.error.v1"
    assert parsed["error"]["type"] == "ParseError"
    assert parsed["error"]["message"]


def test_cli_profile_returns_structured_error_for_malformed_graphml(tmp_path, capsys):
    graph = tmp_path / "broken.graphml"
    graph.write_text("<graphml>", encoding="utf-8")

    code = main(["profile", str(graph), "--format", "graphml"])
    parsed = json.loads(capsys.readouterr().out)

    assert code == 2
    assert parsed["schema"] == "atof.error.v1"
    assert parsed["error"]["type"] == "ParseError"


def test_cli_optimize_returns_structured_error_for_malformed_graphml(tmp_path, capsys):
    graph = tmp_path / "broken.graphml"
    graph.write_text("<graphml>", encoding="utf-8")

    code = main(["optimize", str(graph), "--format", "graphml"])
    parsed = json.loads(capsys.readouterr().out)

    assert code == 2
    assert parsed["schema"] == "atof.error.v1"
    assert parsed["error"]["type"] == "ParseError"


def test_cli_returns_structured_error_for_missing_graph(capsys):
    code = main(["solve", "does-not-exist.edgelist"])
    parsed = json.loads(capsys.readouterr().out)
    assert code == 2
    assert parsed["schema"] == "atof.error.v1"
    assert parsed["error"]["type"] == "FileNotFoundError"
