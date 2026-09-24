import inspect

from experiments import k4_five_seed_replication as replication


def test_five_seed_protocol_is_frozen():
    assert replication.SEEDS == (7, 42, 101, 2024, 8191)
    assert replication.base.SEEDS == (42, 101, 2024)
    assert "seeds" in inspect.signature(replication.base.run).parameters


def test_five_seed_wrapper_passes_seed_grid(monkeypatch, tmp_path):
    observed = {}

    def fake_run(output_path, cache_dir=None, *, seeds):
        observed["output_path"] = output_path
        observed["cache_dir"] = cache_dir
        observed["seeds"] = seeds
        return {"evaluation": {"macro": {}}}

    monkeypatch.setattr(replication.base, "run", fake_run)

    replication.run(tmp_path / "result.json", tmp_path / "cache")

    assert observed["output_path"] == tmp_path / "result.json"
    assert observed["cache_dir"] == tmp_path / "cache"
    assert observed["seeds"] == replication.SEEDS
