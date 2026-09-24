from experiments import k4_five_seed_replication as replication


def test_five_seed_protocol_is_frozen():
    assert replication.SEEDS == (7, 42, 101, 2024, 8191)
    assert replication.base.SEEDS == replication.SEEDS
