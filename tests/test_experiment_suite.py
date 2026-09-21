from experiments.generate_suite import build_suite


def test_suite_is_deterministic():
    first = build_suite(seed=42)
    second = build_suite(seed=42)

    assert list(first) == list(second)

    for name in first:
        assert first[name].number_of_nodes() == second[name].number_of_nodes()
        assert first[name].number_of_edges() == second[name].number_of_edges()



def test_spectral_modularity_bisection_is_balanced():
    import networkx as nx

    from experiments.run_canonical import spectral_modularity_bisection

    graph = nx.path_graph(9)
    result = spectral_modularity_bisection(graph)

    assert result["balance_error"] == 0.0
    assert result["edge_cut"] >= 1
