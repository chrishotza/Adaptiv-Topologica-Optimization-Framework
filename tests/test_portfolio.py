import pytest
import networkx as nx

from atof.portfolio import (
    PortfolioCandidate,
    _run_kahip,
    _validate_candidate_partition,
    optimize_portfolio,
)


def test_portfolio_finds_kernighan_lin_on_karate_club():
    graph = nx.karate_club_graph()
    result = optimize_portfolio(graph, k=2, seed=42, iterations=25, include_optional=False)

    assert result.selected_edge_cut == 10
    assert result.selected_balance_error == 0.0
    assert result.selected_strategy == "NetworkX(Kernighan-Lin)"
    assert result.graph_fingerprint
    assert result.seed == 42
    assert result.iterations == 25




def test_portfolio_candidate_validation_recomputes_metrics():
    graph = nx.cycle_graph(6)
    partition = {node: node % 3 for node in graph.nodes()}
    candidate = PortfolioCandidate(
        id="fake",
        name="fake",
        available=True,
        edge_cut=999,
        balance_error=999.0,
        runtime_seconds=0.1,
        partition=partition,
        backend_version="test",
        postprocess="none",
    )

    validated = _validate_candidate_partition(graph, 3, candidate)

    assert validated.available
    assert validated.edge_cut == 6
    assert validated.balance_error == 0.0
    assert validated.postprocess == "contract_validation"


def test_portfolio_candidate_validation_rejects_bad_node_coverage():
    graph = nx.path_graph(4)
    candidate = PortfolioCandidate(
        id="fake",
        name="fake",
        available=True,
        edge_cut=0,
        balance_error=0.0,
        runtime_seconds=0.1,
        partition={0: 0, 1: 1, 2: 0},
        backend_version="test",
        postprocess="none",
    )

    validated = _validate_candidate_partition(graph, 2, candidate)

    assert not validated.available
    assert validated.partition is None
    assert validated.error
    assert "coverage mismatch" in validated.error


def test_portfolio_is_machine_readable():
    graph = nx.path_graph(10)
    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=False)
    payload = result.to_dict()
    assert payload["schema"] == "atof.portfolio.v1"
    assert payload["version"] == "0.6.0"
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


def test_portfolio_schema_is_published():
    from pathlib import Path
    import json

    schema_path = Path(__file__).parents[1] / "schemas" / "atof-portfolio-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["schema"]["const"] == "atof.portfolio.v1"
    assert "version" in schema["required"]
    assert "candidates" in schema["required"]


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


def test_portfolio_reports_state_of_art_optional_backends(monkeypatch):
    import atof.portfolio as portfolio

    graph = nx.path_graph(8)

    monkeypatch.setattr(
        portfolio,
        "_run_kaminpar",
        lambda graph, seed, k, context_name: (
            {node: node % k for node in graph},
            7,
            0.0,
        ),
    )
    monkeypatch.setattr(
        portfolio,
        "_run_mtkahypar",
        lambda graph, seed, k, preset: (
            {node: node % k for node in graph},
            7,
            0.0,
        ),
    )

    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=True)
    ids = {item.id for item in result.candidates}
    assert "kaminpar-default" in ids
    assert "kaminpar-strong" in ids
    assert "mtkahypar-default" in ids
    assert "mtkahypar-quality" in ids


def test_backend_manifest_includes_state_of_art_backends():
    from atof.backends import inspect_backends

    ids = {item.id for item in inspect_backends()}
    assert "kaminpar-default" in ids
    assert "kaminpar-strong" in ids
    assert "mtkahypar-default" in ids
    assert "mtkahypar-quality" in ids
