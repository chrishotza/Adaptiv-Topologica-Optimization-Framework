from __future__ import annotations

import json

import networkx as nx

from atof.ai import build_ai_manifest, build_doctor_report, compact_result
from atof.cli import main


def test_ai_manifest_is_stable_and_compact():
    manifest = build_ai_manifest()
    assert manifest["schema"] == "atof.ai.v1"
    assert manifest["name"] == "atof"
    assert manifest["capabilities"]["portfolio"]["k"] == ">=2"
    assert manifest["capabilities"]["portfolio"]["result_schema"] == "atof.portfolio.v1"
    assert any("compact profile is bounded" in item for item in manifest["limits"])
    assert manifest["capabilities"]["engine"]["result_schema"] == "atof.optimize.v1"
    assert manifest["commands"]["compare"] == "atof compare <graph> [--k N]"
    assert manifest["capabilities"]["comparison"]["result_schema"] == "atof.compare.v1"
    assert manifest["commands"]["doctor"] == "atof doctor"
    assert "not universally optimal" in manifest["claim_policy"]["non_claims"]
    assert manifest["commands"]["short_flags"]["compact"] == "-c"
    assert manifest["commands"]["short_flags"]["partition_output"] == "-p"
    assert manifest["capabilities"]["portfolio"]["result_schema"] == "atof.portfolio.v1"


def test_compact_result_drops_verbose_fields():
    payload = {
        "schema": "atof.portfolio.v1",
        "mode": "portfolio",
        "version": "0.6.0",
        "strategy": {"selected": "NetworkX(Kernighan-Lin)"},
        "graph": {"nodes": 4, "edges": 3},
        "topology": {"many": "fields"},
        "result": {
            "k": 2,
            "edge_cut": 1,
            "balance_error": 0.0,
            "partition": {"a": 0, "b": 1},
        },
        "candidates": [
            {
                "id": "networkx-kl",
                "name": "NetworkX(Kernighan-Lin)",
                "available": True,
                "edge_cut": 1,
                "runtime_seconds": 0.01,
                "error": None,
            }
        ],
    }
    compact = compact_result(payload)
    assert "topology" not in compact
    assert "partition" not in compact["result"]
    assert compact["result"]["edge_cut"] == 1
    assert compact["schema"] == "atof.portfolio.v1"


def test_ai_cli_emits_json(capsys):
    assert main(["ai"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["schema"] == "atof.ai.v1"


def test_doctor_cli_emits_json(capsys):
    assert main(["doctor"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["schema"] == "atof.doctor.v1"
    assert parsed["portfolio_ready"] is True


def test_compact_profile_cli(tmp_path, capsys):
    source = tmp_path / "graph.edgelist"
    source.write_text("a b\nb c\nc d\n", encoding="utf-8")
    assert main(["profile", str(source), "--compact"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["mode"] == "profile"
    assert parsed["graph"]["nodes"] == 4
    assert "topology" not in parsed
    assert parsed["provenance"]["graph_fingerprint"]


def test_compact_portfolio_cli(capsys):
    from atof.portfolio import optimize_portfolio

    graph = nx.karate_club_graph()
    result = optimize_portfolio(graph, include_optional=False)
    payload = compact_result({**result.to_dict(), "version": "0.6.0"})
    assert payload["result"]["k"] == 2
    assert payload["result"]["edge_cut"] == 10
    assert payload["parameters"]["seed"] == 42
    assert payload["provenance"]["graph_fingerprint"]


def test_solve_shortcut_cli(tmp_path, capsys):
    source = tmp_path / "graph.edgelist"
    source.write_text("a b\nb c\nc d\n", encoding="utf-8")
    assert main(["solve", str(source)]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["mode"] == "portfolio"
    assert parsed["result"]["k"] == 2


def test_ai_manifest_compact_size_is_bounded():
    encoded = json.dumps(build_ai_manifest(), separators=(",", ":"), sort_keys=True)
    assert len(encoded) < 3000


def test_doctor_report_is_machine_readable():
    report = build_doctor_report()
    assert report["schema"] == "atof.doctor.v1"
    assert report["portfolio_ready"] is True
    assert {item["id"] for item in report["backends"]} >= {
        "bloc", "networkx-kl", "metis", "kahip"
    }


def test_solve_shortcut_exports_partition(tmp_path, capsys):
    source = tmp_path / "graph.edgelist"
    source.write_text("a b\nb c\nc d\n", encoding="utf-8")
    output = tmp_path / "partition.json"

    assert main([
        "solve",
        str(source),
        "--partition-output",
        str(output),
    ]) == 0

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert len(payload) == 4
    assert set(payload[0]) == {"node", "block"}
