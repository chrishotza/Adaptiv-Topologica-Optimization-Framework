import networkx as nx

from atof.portfolio import optimize_portfolio


def test_portfolio_finds_kernighan_lin_on_karate_club():
    graph = nx.karate_club_graph()
    result = optimize_portfolio(graph, k=2, seed=42, iterations=25, include_optional=False)

    assert result.selected_edge_cut == 10
    assert result.selected_balance_error == 0.0
    assert result.selected_strategy == "NetworkX(Kernighan-Lin)"


def test_portfolio_is_machine_readable():
    graph = nx.path_graph(10)
    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=False)
    payload = result.to_dict()
    assert payload["mode"] == "portfolio"
    assert payload["result"]["k"] == 2
    assert len(payload["result"]["partition"]) == 10
    assert len(payload["candidates"]) >= 3


def test_portfolio_reports_optional_backends_when_unavailable():
    graph = nx.path_graph(10)
    result = optimize_portfolio(graph, k=2, seed=42, iterations=5, include_optional=True)
    payload = result.to_dict()
    names = {item["name"] for item in payload["candidates"]}
    assert "METIS(PyMetis)" in names
    assert "KaHIP(KaFFPa-Strong)" in names
