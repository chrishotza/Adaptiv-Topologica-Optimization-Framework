from __future__ import annotations

import json

import networkx as nx

from atof.ai import build_ai_manifest, compact_result
from atof.cli import main


def test_ai_manifest_is_stable_and_compact():
    manifest = build_ai_manifest()
    assert manifest["schema"] == "atof.ai.v1"
    assert manifest["name"] == "atof"
    assert manifest["commands"]["ai"] == "atof ai"
    assert manifest["portfolio"]["k"] == 2


def test_compact_result_drops_verbose_fields():
    payload = {
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


def test_ai_cli_emits_json(capsys):
    assert main(["ai"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["schema"] == "atof.ai.v1"


def test_compact_profile_cli(tmp_path, capsys):
    source = tmp_path / "graph.edgelist"
    source.write_text("a b\nb c\nc d\n", encoding="utf-8")
    assert main(["profile", str(source), "--compact"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["mode"] == "profile"
    assert parsed["graph"]["nodes"] == 4
    assert "topology" not in parsed


def test_compact_portfolio_cli(capsys):
    graph = nx.karate_club_graph()
    from atof.portfolio import optimize_portfolio

    result = optimize_portfolio(graph, include_optional=False)
    payload = compact_result({**result.to_dict(), "version": "0.6.0"})
    assert payload["result"]["k"] == 2
    assert payload["result"]["edge_cut"] == 10
