from experiments.k8_five_seed_feature_representation_diagnostic import EXPECTED_GROUPS

def test_expected_feature_groups():
    assert EXPECTED_GROUPS == ("all", "degree_hub", "mesoscopic", "global_paths")
