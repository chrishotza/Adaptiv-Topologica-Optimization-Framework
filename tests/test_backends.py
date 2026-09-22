from atof.ai import build_ai_manifest
from atof.backends import inspect_backends


def test_ai_manifest_exposes_state_of_art_backends():
    backends = build_ai_manifest(full=True)["capabilities"]["portfolio"]["backends"]
    assert "KaMinPar default (optional)" in backends
    assert "KaMinPar strong (optional)" in backends
    assert "Mt-KaHyPar default (optional)" in backends
    assert "Mt-KaHyPar quality (optional)" in backends


def test_backend_registry_exposes_state_of_art_variants():
    ids = {backend.id for backend in inspect_backends()}
    assert {
        "kaminpar-default",
        "kaminpar-strong",
        "mtkahypar-default",
        "mtkahypar-quality",
    } <= ids
