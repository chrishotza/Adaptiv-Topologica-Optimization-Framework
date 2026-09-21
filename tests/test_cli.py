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
    assert capsys.readouterr().out.strip() == "0.5.0"
