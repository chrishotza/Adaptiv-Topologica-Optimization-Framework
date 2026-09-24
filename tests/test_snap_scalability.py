from experiments.run_snap_scalability import run_snap_scalability


def test_snap_scalability_runner_without_network(tmp_path, monkeypatch):
    import networkx as nx

    def fake_download(dataset, *, cache_dir=None, timeout=60.0):
        graph = nx.path_graph(max(8, min(dataset.nodes or 8, 20)))
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
        "experiments.run_snap_scalability.download_snap_dataset",
        fake_download,
    )

    output = tmp_path / "scalability.json"
    payload = run_snap_scalability(output_path=output, cache_dir=tmp_path / "cache")

    assert output.exists()
    assert len(payload["rows"]) == 3
    assert payload["profiler_limits"]["mode"] == "bounded"
    assert all(row["profile_mode"] == "bounded" for row in payload["rows"])
    assert all("profile_seconds" in row for row in payload["rows"])
