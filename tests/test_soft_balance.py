import networkx as nx

from atof.soft_balance import SoftBalanceReloc


def test_soft_balance_is_deterministic_and_finally_balanced():
    graph = nx.path_graph(64)
    first = SoftBalanceReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=10,
        balance_slack=1,
        balance_penalty=0.5,
    )
    second = SoftBalanceReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=10,
        balance_slack=1,
        balance_penalty=0.5,
    )

    assert first.partition == second.partition
    assert first.edge_cut == second.edge_cut
    assert first.trace == second.trace
    assert first.balance_error == 0.0


def test_soft_balance_can_cross_strict_balance_boundary():
    graph = nx.path_graph(64)
    result = SoftBalanceReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=5,
        balance_slack=1,
        balance_penalty=0.0,
    )

    assert result.balance_error == 0.0
    assert any(row["balance_error"] > 0 for row in result.trace)


def test_soft_balance_matches_strict_when_slack_is_zero_and_penalty_is_high():
    graph = nx.path_graph(64)
    result = SoftBalanceReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=5,
        balance_slack=0,
        balance_penalty=10.0,
    )

    assert result.balance_error == 0.0
