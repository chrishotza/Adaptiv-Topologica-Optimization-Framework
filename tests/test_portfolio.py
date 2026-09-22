import pytest
import networkx as nx

from atof.portfolio import _run_kahip, optimize_portfolio


def test_portfolio_finds_kernighan_lin_on_karate_club():
    graph = nx.karate_club_graph()
    result = optimize_portfolio(graph, k=2, seed=42, iterations=25, include_optional=False)

    assert result.selected_edge_cut == 10
    assert result.selected_balance_error == 0.0
    assert result.selected_strategy == "NetworkX(Kernighan-Lin)"
    assert result.graph_fingerprint
    assert result.seed == 42
    assert result.iterations == 25


def test_portfolio_is_machine_readable():
    graph = nx.path_graph(10)
    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=False)
    payload = result.to_dict()
    assert payload["mode"] == "portfolio"
    assert payload["result"]["k"] == 2
    assert len(payload["result"]["partition"]) == 10
    assert len(payload["candidates"]) >= 3
    assert payload["parameters"]["seed"] == 42
    assert payload["provenance"]["graph_fingerprint"] == result.graph_fingerprint




def test_portfolio_supports_kway_without_optional_backends():
    graph = nx.cycle_graph(12)
    result = optimize_portfolio(
        graph,
        k=3,
        seed=42,
        iterations=5,
        include_optional=False,
    )
    payload = result.to_dict()

    assert payload["parameters"]["k"] == 3
    assert payload["result"]["k"] == 3
    assert payload["result"]["balance_error"] == 0.0
    assert len(payload["result"]["partition"]) == 12
    assert set(payload["result"]["partition"].values()) == {0, 1, 2}
    networkx_candidate = next(
        item for item in payload["candidates"] if item["id"] == "networkx-kl"
    )
    assert not networkx_candidate["available"]
    assert "k=2" in networkx_candidate["error"]




def test_kahip_kway_balance_is_measured_across_all_blocks(monkeypatch):
    graph = nx.cycle_graph(6)

    class FakeKaHIP:
        @staticmethod
        def kaffpa(*args):
            return 0, [0, 0, 0, 0, 1, 1]

    monkeypatch.setitem(__import__("sys").modules, "kahip", FakeKaHIP())

    partition, _, balance = _run_kahip(graph, seed=42, k=3)

    assert set(partition.values()) == {0, 1, 2}
    counts = [list(partition.values()).count(block) for block in range(3)]
    assert counts == [2, 2, 2]
    assert balance == 0.0


def test_portfolio_reports_optional_backends_when_unavailable():
    graph = nx.path_graph(10)
    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=True)
    payload = result.to_dict()
    names = {item["name"] for item in payload["candidates"]}
    assert "METIS(PyMetis)" in names
    assert "KaHIP(KaFFPa-Strong)" in names



def test_portfolio_rejects_node_ids_that_collide_after_serialization():
    graph = nx.Graph()
    graph.add_nodes_from([1, "1"])

    with pytest.raises(ValueError, match="unique after string serialization"):
        optimize_portfolio(graph, include_optional=False)

def test_portfolio_rejects_unsupported_graph_models():
    directed = nx.DiGraph([(0, 1), (1, 2)])
    with pytest.raises(ValueError, match="undirected"):
        optimize_portfolio(directed, include_optional=False)

    multigraph = nx.MultiGraph([(0, 1), (0, 1)])
    with pytest.raises(ValueError, match="simple graph"):
        optimize_portfolio(multigraph, include_optional=False)


def test_portfolio_is_reproducible_for_same_seed():
    graph = nx.karate_club_graph()
    first = optimize_portfolio(graph, seed=42, include_optional=False).to_dict(
        include_partition=True
    )
    second = optimize_portfolio(graph, seed=42, include_optional=False).to_dict(
        include_partition=True
    )
    assert first["result"]["partition"] == second["result"]["partition"]
    assert first["result"]["edge_cut"] == second["result"]["edge_cut"]
    assert first["provenance"]["graph_fingerprint"] == second["provenance"]["graph_fingerprint"]
