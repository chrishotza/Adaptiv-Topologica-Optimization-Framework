import networkx as nx

from atof.datasets import standard_reference_corpus


def test_standard_reference_corpus_is_deterministic():
    datasets = standard_reference_corpus()

    assert [item.name for item in datasets] == [
        "karate_club",
        "davis_southern_women",
        "florentine_families",
        "les_miserables",
    ]

    for dataset in datasets:
        graph = dataset.load()
        assert isinstance(graph, nx.Graph)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0
        assert nx.number_of_selfloops(graph) == 0
