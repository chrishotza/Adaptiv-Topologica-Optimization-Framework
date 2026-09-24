import inspect

from atof.portfolio import _run_kahip, _run_metis
from experiments.k4_routing_generalization import FEATURES, K, SEEDS, STRATEGIES, _integer_feasible_imbalance


def test_k4_protocol_manifest_is_frozen() -> None:
    assert K == 4
    assert SEEDS == (42, 101, 2024)
    assert len(STRATEGIES) == 8
    assert "networkx-kl" not in STRATEGIES
    assert STRATEGIES == (
        "bloc", "bloc-affinity", "metis", "kahip",
        "kaminpar", "kaminpar-strong", "mtkahypar", "mtkahypar-quality",
    )
    assert len(FEATURES) == 11
    assert "modularity" in FEATURES


def test_metis_runner_keeps_recursive_product_default() -> None:
    assert inspect.signature(_run_metis).parameters["recursive"].default is True


def test_integer_feasible_imbalance_is_minimum_for_floor_ceil_balance():
    class G:
        def number_of_nodes(self):
            return 15

    assert _integer_feasible_imbalance(G(), 4) == 4 / 3.75 - 1.0


def test_backend_product_defaults_remain_locked():
    assert inspect.signature(_run_metis).parameters["recursive"].default is True
    assert inspect.signature(_run_metis).parameters["ufactor"].default is None
    assert inspect.signature(_run_kahip).parameters["imbalance"].default == 0.03


def test_tiny_graph_padding_isolated_and_reversible():
    import networkx as nx
    from experiments.k4_routing_generalization import _pad_isolated_nodes, _strip_padding

    graph = nx.path_graph(15)
    padded, padding = _pad_isolated_nodes(graph, 4)
    assert padded.number_of_nodes() == 16
    assert len(padding) == 1
    assert set(padded) == set(graph) | set(padding)
    membership = {node: index % 4 for index, node in enumerate(padded)}
    stripped = _strip_padding(graph, membership, padding)
    assert set(stripped) == set(graph)
