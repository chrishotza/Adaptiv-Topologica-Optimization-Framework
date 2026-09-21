import networkx as nx

from atof.benchmark import benchmark_bloc


def test_benchmark_records_are_serializable():
    rows = benchmark_bloc(
        [("cycle", nx.cycle_graph(8))],
        k=2,
        seeds=(42,),
        iterations=2,
    )
    assert len(rows) == 2
    assert {row["variant"] for row in rows} == {"baseline", "affinity"}
    assert all("trace" in row and row["seed"] == 42 for row in rows)
