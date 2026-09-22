from atof.ai import build_ai_manifest
from atof.backends import inspect_backends


def test_ai_manifest_exposes_state_of_art_backends():
    backends = build_ai_manifest(full=True)["capabilities"]["portfolio"]["backends"]
    assert "KaMinPar default (optional)" in backends
    assert "KaMinPar strong (optional)" in backends
    assert "Mt-KaHyPar default (optional)" in backends
    assert "Mt-KaHyPar quality (optional)" in backends


def test_backend_registry_exposes_state_of_art_variants():
    ids = {backend.id for backend in inspect_backends()}
    assert {
        "kaminpar-default",
        "kaminpar-strong",
        "mtkahypar-default",
        "mtkahypar-quality",
    } <= ids



def test_kaminpar_zero_epsilon_uses_exact_absolute_caps(monkeypatch):
    import sys
    import types
    import networkx as nx
    import atof.backends as backends

    graph = nx.cycle_graph(6)
    observed = {}

    class FakeInstance:
        def compute_partition(self, loaded, max_block_weights):
            observed["max_block_weights"] = list(max_block_weights)
            return [0, 0, 1, 1, 2, 2]

    monkeypatch.setattr(
        backends,
        "_kaminpar_graph",
        lambda graph, graph_id: object(),
    )
    monkeypatch.setattr(
        backends,
        "_kaminpar_context",
        lambda context_name: FakeInstance(),
    )
    monkeypatch.setitem(
        sys.modules,
        "kaminpar",
        types.SimpleNamespace(reseed=lambda seed: None),
    )

    partition, edge_cut, balance, runtime = backends._run_kaminpar_in_process(
        graph,
        graph_id="test-cycle",
        seed=42,
        k=3,
        context_name="default",
    )

    assert observed["max_block_weights"] == [2, 2, 2]
    assert sorted(partition.values()) == [0, 0, 1, 1, 2, 2]
    assert balance == 0.0
    assert edge_cut == 3
    assert runtime >= 0.0
