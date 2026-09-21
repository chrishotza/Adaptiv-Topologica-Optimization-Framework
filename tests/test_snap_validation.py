from pathlib import Path

from atof.snap import snap_reference_corpus
from experiments.run_snap_validation import run_snap_validation


def test_snap_validation_with_injected_cache_guard(tmp_path, monkeypatch):
    datasets = snap_reference_corpus()

    def fake_download(dataset, *, cache_dir=None, timeout=60.0):
        import networkx as nx

        graph = nx.cycle_graph(max(8, min(dataset.nodes or 8, 20)))
        return graph, {
            "name": dataset.name,
            "source": dataset.source,
            "reference_url": dataset.reference_url,
            "download_url": dataset.download_url,
            "sha256": "test",
            "bytes": 0,
            "loaded_nodes": graph.number_of_nodes(),
            "loaded_edges": graph.number_of_edges(),
        }

    monkeypatch.setattr(
        "experiments.run_snap_validation.download_snap_dataset",
        fake_download,
    )

    output = tmp_path / "snap.json"
    payload = run_snap_validation(
        output_path=output,
        seeds=(42,),
        iterations=1,
        bootstrap_resamples=50,
        cache_dir=Path(tmp_path) / "cache",
    )

    assert output.exists()
    assert len(payload["datasets"]) == 4
    assert len(payload["rows"]) == 24
    assert payload["routing"]["graphs"] == 4
    assert 0.0 <= payload["routing"]["learned_oracle_agreement"] <= 1.0
