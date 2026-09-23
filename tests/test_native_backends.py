import sys

import networkx as nx

from atof.native_backends import run_kaminpar, run_mtkahypar


def test_kaminpar_adapter_maps_backend_membership(monkeypatch):
    graph = nx.cycle_graph(6)

    class FakeFormat:
        METIS = object()

    class FakeContext:
        pass

    class FakeKaminPar:
        def __init__(self, num_threads, context):
            assert num_threads == 1

        def compute_partition(self, backend_graph, k, eps):
            assert k == 3
            assert eps == 0.0
            return [0, 0, 1, 1, 2, 2]

    class FakeModule:
        GraphFileFormat = FakeFormat
        def default_context(self):
            return FakeContext()
        def strong_context(self):
            return FakeContext()
        def reseed(self, seed):
            assert seed == 42
        KaMinPar = FakeKaminPar

        def load_graph(self, filename, fmt, compress=False):
            assert fmt is FakeFormat.METIS
            assert compress is False
            return object()

    monkeypatch.setitem(sys.modules, "kaminpar", FakeModule())

    partition, cut, balance = run_kaminpar(graph, seed=42, k=3)

    assert set(partition.values()) == {0, 1, 2}
    assert cut == 3
    assert balance == 0.0


def test_mtkahypar_adapter_maps_block_ids(monkeypatch):
    graph = nx.cycle_graph(6)

    class PresetType:
        DEFAULT = "default"
        QUALITY = "quality"

    class Objective:
        CUT = "cut"

    class Context:
        def set_partitioning_parameters(self, k, epsilon, objective):
            assert (k, epsilon, objective) == (3, 0.0, Objective.CUT)

        logging = False

    class Partitioned:
        def block_id(self, node):
            return [0, 0, 1, 1, 2, 2][node]

    class BackendGraph:
        def partition(self, context):
            return Partitioned()

    class Initializer:
        def context_from_preset(self, preset):
            assert preset == PresetType.DEFAULT
            return Context()

        def create_graph(self, context, num_nodes, num_edges, edges):
            assert num_nodes == 6
            assert num_edges == 6
            assert len(edges) == 6
            return BackendGraph()

    class FakeModule:
        PresetType = PresetType
        Objective = Objective

        def initialize(self, threads, print_warnings=True):
            assert threads == 1
            assert print_warnings is False
            return Initializer()

        def set_seed(self, seed):
            assert seed == 42

    monkeypatch.setitem(sys.modules, "mtkahypar", FakeModule())

    partition, cut, balance = run_mtkahypar(graph, seed=42, k=3)

    assert set(partition.values()) == {0, 1, 2}
    assert cut == 3
    assert balance == 0.0
