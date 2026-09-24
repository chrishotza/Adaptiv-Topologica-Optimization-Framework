from pathlib import Path
import json
from experiments.k8_degree_hub_selector_budget_control import run

def test_schema_fixture(tmp_path: Path):
    payload = {
        "schema_version":"1.0",
        "k":8,
        "seeds":[7,42,101,2024,8191],
        "candidate_strategies":["a"]*8,
        "graph_manifest":[]
    }
    path=tmp_path/"b.json"
    path.write_text(json.dumps(payload))
    assert path.exists()
