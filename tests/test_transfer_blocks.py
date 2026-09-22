from experiments.run_transfer_block import BLOCKS


def test_block_manifest_covers_exactly_26_graphs():
    names = [
        name
        for _, graph_names in BLOCKS.values()
        for name in graph_names
    ]
    assert len(names) == 26
    assert len(set(names)) == 26


def test_block_manifest_has_expected_corpora():
    assert {corpus for corpus, _ in BLOCKS.values()} == {
        "development",
        "external",
        "snap",
        "snap_scalability",
        "dimacs",
    }


def test_large_graphs_are_isolated_blocks():
    assert BLOCKS["snap_scalability_ca_grqc"][1] == ("ca_grqc",)
    assert BLOCKS["snap_scalability_ca_hepth"][1] == ("ca_hepth",)
    assert BLOCKS["snap_scalability_wiki_vote"][1] == ("wiki_vote",)
    assert BLOCKS["dimacs_as_22july06"][1] == ("as_22july06",)
    assert BLOCKS["dimacs_astro_ph"][1] == ("astro_ph",)
    assert BLOCKS["dimacs_pgp_giant"][1] == ("pgp_giant",)
