from experiments.generate_suite import build_suite


def test_suite_is_deterministic():
    first = build_suite(seed=42)
    second = build_suite(seed=42)

    assert list(first) == list(second)

    for name in first:
        assert first[name].number_of_nodes() == second[name].number_of_nodes()
        assert first[name].number_of_edges() == second[name].number_of_edges()
