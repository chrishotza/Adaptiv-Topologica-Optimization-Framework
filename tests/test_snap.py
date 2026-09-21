import gzip
import io

import networkx as nx

from atof.snap import parse_snap_bytes, snap_reference_corpus, snap_scalability_corpus


def _payload() -> bytes:
    raw = b"# nodes edges\n10 11\n11 12\n12 10\n12 12\n"
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as stream:
        stream.write(raw)
    return buffer.getvalue()


def test_snap_parser_normalizes_to_simple_undirected():
    graph = parse_snap_bytes(_payload(), directed=True)

    assert isinstance(graph, nx.Graph)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 3
    assert nx.number_of_selfloops(graph) == 0


def test_snap_reference_registry_has_four_empirical_graphs():
    datasets = snap_reference_corpus()

    assert [item.name for item in datasets] == [
        "c_elegans_frontal",
        "florida_bay",
        "s_cerevisiae",
        "email_eu_core",
    ]
    assert all(item.download_url.endswith(".txt.gz") for item in datasets)
    assert all(item.reference_url.startswith("https://snap.stanford.edu/") for item in datasets)


def test_snap_scalability_registry_is_separate():
    datasets = snap_scalability_corpus()

    assert [item.name for item in datasets] == [
        "ca_grqc",
        "ca_hepth",
        "wiki_vote",
    ]
    assert all(item.nodes is not None and item.nodes >= 5000 for item in datasets)
