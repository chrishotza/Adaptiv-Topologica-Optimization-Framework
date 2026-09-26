from experiments.k8_external_runtime_preflight import GRAPH, K, SEED


def test_preflight_scope_is_small_and_fixed():
    assert GRAPH["name"] == "ego_facebook"
    assert GRAPH["declared_nodes"] == 4039
    assert GRAPH["declared_edges"] == 88234
    assert K == 8
    assert SEED == 5003
