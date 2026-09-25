import json
from pathlib import Path

from experiments.k8_degree_hub_selector_budget_control import RANDOM_REPEATS

def test_protocol_constants():
    assert RANDOM_REPEATS == 500

def test_control_contract(tmp_path: Path):
    payload = {
        "schema_version":"1.0",
        "k":8,
        "seeds":[7,42,101,2024,8191],
        "candidate_strategies":[f"s{i}" for i in range(8)],
        "graph_manifest":[]
    }
    path=tmp_path/"b.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert json.loads(path.read_text())["k"] == 8
