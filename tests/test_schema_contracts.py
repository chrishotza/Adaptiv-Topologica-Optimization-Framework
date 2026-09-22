from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from jsonschema import Draft202012Validator

from atof.ai import build_ai_manifest, compact_result
from atof.portfolio import optimize_portfolio
from atof.product import optimize_graph


ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _assert_valid(payload: dict, schema_name: str) -> None:
    schema = _schema(schema_name)
    Draft202012Validator(schema).validate(payload)


def test_ai_manifest_matches_runtime_schema():
    _assert_valid(build_ai_manifest(), "atof-ai-v1.schema.json")


def test_portfolio_full_and_compact_results_match_schema():
    graph = nx.cycle_graph(8)
    full = optimize_portfolio(
        graph,
        k=2,
        seed=42,
        iterations=5,
        include_optional=False,
    ).to_dict()
    compact = compact_result(full)

    _assert_valid(full, "atof-portfolio-v1.schema.json")
    _assert_valid(compact, "atof-portfolio-v1.schema.json")


def test_engine_full_and_compact_results_match_schema():
    graph = nx.path_graph(8)
    full = optimize_graph(
        graph,
        k=3,
        seed=42,
        iterations=4,
        variant="baseline",
    ).to_dict()
    compact = compact_result(full)

    _assert_valid(full, "atof-optimize-v1.schema.json")
    _assert_valid(compact, "atof-optimize-v1.schema.json")


def test_compare_results_match_schema():
    import networkx as nx

    from atof.comparison import compare_graph, compact_comparison

    payload = compare_graph(nx.cycle_graph(8), k=2, seed=42, iterations=3)
    compact = compact_comparison(payload)

    _assert_valid(payload, "atof-compare-v1.schema.json")
    _assert_valid(compact, "atof-compare-v1.schema.json")
