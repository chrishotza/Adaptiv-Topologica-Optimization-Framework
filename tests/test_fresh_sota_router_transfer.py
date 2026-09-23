import json

from experiments.fresh_sota_router_transfer import run_analysis


def _make_graph(strategy_shift: str, corpus: str, graph: str) -> tuple[str, dict]:
    strategies = [
        "metis",
        "kahip",
        "kaminpar_default",
        "kaminpar_strong",
        "mtkahypar_default",
        "mtkahypar_quality",
        "bloc_reloc_baseline",
        "bloc_reloc_affinity",
        "bloc_reloc_hybrid_fixed",
        "bloc_reloc_adaptive",
        "kernighan_lin",
    ]
    metrics = {}
    for strategy in strategies:
        value = 20.0
        if strategy == strategy_shift:
            value = 10.0
        metrics[strategy] = {"edge_cut": value, "runtime_seconds": 1.0}

    graph_id = f"{corpus}/{graph}"
    return graph_id, {
        "matched": True,
        "best_quality": strategy_shift,
        "best_edge_cut": 10.0,
        "strategies": metrics,
    }


def test_fresh_router_transfer_is_leave_one_corpus_out(tmp_path):
    graph_summaries = {}
    graph_metadata = {}
    for graph, winner in (("a", "metis"), ("b", "kaminpar_default")):
        graph_id, summary = _make_graph(winner, "c1", graph)
        graph_summaries[graph_id] = summary
        graph_metadata[graph_id] = {
            "corpus": "c1",
            "graph": graph,
            "topology": {
                "density": 0.1 if graph == "a" else 0.8,
                "avg_degree": 2.0 if graph == "a" else 8.0,
                "degree_std": 0.1,
                "hub_ratio": 1.0,
                "degree_gini": 0.1,
                "clustering": 0.1,
                "transitivity": 0.1,
                "core_number": 1.0,
                "diameter": 4.0,
                "avg_path_length": 2.0,
                "modularity": 0.1,
            },
            "regime_signature": {},
        }

    graph_id, summary = _make_graph("kahip", "c2", "c")
    graph_summaries[graph_id] = summary
    graph_metadata[graph_id] = {
        "corpus": "c2",
        "graph": "c",
        "topology": {
            "density": 0.5,
            "avg_degree": 5.0,
            "degree_std": 0.1,
            "hub_ratio": 1.0,
            "degree_gini": 0.1,
            "clustering": 0.1,
            "transitivity": 0.1,
            "core_number": 1.0,
            "diameter": 3.0,
            "avg_path_length": 1.5,
            "modularity": 0.1,
        },
        "regime_signature": {},
    }

    source = tmp_path / "benchmark.json"
    source.write_text(
        json.dumps({
            "commit_sha": "test",
            "candidate_strategies": list(graph_summaries[next(iter(graph_summaries))]["strategies"]),
            "graph_summaries": graph_summaries,
            "graph_metadata": graph_metadata,
        }),
        encoding="utf-8",
    )

    output = tmp_path / "router.json"
    payload = run_analysis(source, output)

    assert output.exists()
    assert payload["matched_graphs"] == 3
    assert set(payload["corpora"]) == {"c1", "c2"}
    assert set(payload["pooled"]) == {
        "nearest_vs_majority",
        "nearest_vs_global_mean",
        "centroid_vs_majority",
        "centroid_vs_global_mean",
    }
