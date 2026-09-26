from experiments.k8_external_solver_unit import EXTERNAL_SEEDS, STRATEGIES
from experiments.k8_external_solver_aggregate import DATASETS, ROUTER_CONFIGS


def test_matrix_scope_is_frozen():
    assert set(DATASETS) == {"ca_astroph", "ca_condmat"}
    assert set(EXTERNAL_SEEDS) == {5003, 7003, 9001, 12011, 16001}
    assert set(STRATEGIES) == {
        "bloc",
        "bloc-affinity",
        "metis",
        "kahip",
        "kaminpar",
        "kaminpar-strong",
        "mtkahypar",
        "mtkahypar-quality",
    }


def test_router_scope_is_frozen():
    assert set(ROUTER_CONFIGS) == {"all_iqr_l2", "global_paths_iqr_l2"}

# Workflow activation commit.
