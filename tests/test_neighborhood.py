import networkx as nx
import pytest

from atof.neighborhood import NeighborhoodCreditController
from atof.strategies import BLOCReloc


def test_neighborhood_credit_controller_routes_by_marginal_credit():
    controller = NeighborhoodCreditController(threshold=1.15, max_skips=2)
    controller.observe_local(10.0, 100)
    assert controller.should_hybrid()
    controller.record_decision(True)
    controller.observe_hybrid(3.0, 20)
    controller.observe_local(20.0, 100)
    assert controller.hybrid_credit < controller.local_credit * 1.15
    assert not controller.should_hybrid()
    controller.record_decision(False)
    assert not controller.should_hybrid()
    controller.record_decision(False)
    assert controller.should_hybrid()


def test_credit_policy_is_deterministic_for_fixed_seed():
    graph = nx.cycle_graph(20)
    first = BLOCReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=25,
        hybrid_period=5,
        hybrid_samples=100,
        hybrid_policy="credit",
    )
    second = BLOCReloc(graph, k=2, seed=42, variant="baseline").refine(
        iterations=25,
        hybrid_period=5,
        hybrid_samples=100,
        hybrid_policy="credit",
    )
    assert first.edge_cut == second.edge_cut
    assert first.partition == second.partition
    assert first.trace == second.trace


@pytest.mark.parametrize("policy", ["fixed", "adaptive", "credit"])
def test_supported_hybrid_policies(policy):
    result = BLOCReloc(nx.path_graph(12), k=4, seed=42).refine(
        iterations=5,
        hybrid_period=5,
        hybrid_samples=20,
        hybrid_policy=policy,
    )
    assert result.iterations == 5
