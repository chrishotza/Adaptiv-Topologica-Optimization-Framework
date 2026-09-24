from atof.routing import FEATURES

def test_feature_list_is_frozen():
    assert len(FEATURES) == 11
    assert "density" in FEATURES
    assert "modularity" in FEATURES
