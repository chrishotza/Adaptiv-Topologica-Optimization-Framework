import json

from atof.ai import build_doctor_report
from atof.backends import BackendInfo


def test_doctor_portfolio_ready_does_not_depend_on_networkx(monkeypatch):
    monkeypatch.setattr(
        "atof.ai.inspect_backends",
        lambda: (
            BackendInfo(
                id="bloc",
                name="BLOC-RELOC",
                package="atof",
                optional=False,
                available=True,
                version="0.6.0",
            ),
            BackendInfo(
                id="networkx-kl",
                name="NetworkX Kernighan-Lin",
                package="networkx",
                optional=False,
                available=False,
                version=None,
                error="simulated unavailable",
            ),
        ),
    )

    report = build_doctor_report(full=True)

    assert report["portfolio_ready"] is True
    assert report["backends"][0]["id"] == "bloc"
    assert report["backends"][1]["id"] == "networkx-kl"


def test_doctor_portfolio_ready_is_false_when_no_backend_is_available(monkeypatch):
    monkeypatch.setattr(
        "atof.ai.inspect_backends",
        lambda: (
            BackendInfo(
                id="bloc",
                name="BLOC-RELOC",
                package="atof",
                optional=False,
                available=False,
                version=None,
                error="simulated unavailable",
            ),
            BackendInfo(
                id="networkx-kl",
                name="NetworkX Kernighan-Lin",
                package="networkx",
                optional=False,
                available=False,
                version=None,
                error="simulated unavailable",
            ),
        ),
    )

    report = build_doctor_report(full=True)

    assert report["portfolio_ready"] is False


def test_doctor_report_is_json_serializable():
    payload = build_doctor_report(full=True)
    json.dumps(payload, sort_keys=True)


def test_doctor_reports_kway_capability_separately(monkeypatch):
    monkeypatch.setattr(
        "atof.ai.inspect_backends",
        lambda: (
            BackendInfo(
                id="networkx-kl",
                name="NetworkX Kernighan-Lin",
                package="networkx",
                optional=False,
                available=True,
                version="3.0",
            ),
        ),
    )

    report = build_doctor_report(full=True)

    assert report["portfolio_ready"] is True
    assert report["portfolio_kway_ready"] is False
    assert report["portfolio_kway_backends"] == []


def test_doctor_reports_available_kway_backends(monkeypatch):
    monkeypatch.setattr(
        "atof.ai.inspect_backends",
        lambda: (
            BackendInfo(
                id="bloc",
                name="BLOC-RELOC",
                package="atof",
                optional=False,
                available=True,
                version="0.6.0",
            ),
            BackendInfo(
                id="metis",
                name="METIS via PyMetis",
                package="pymetis",
                optional=True,
                available=True,
                version="2025.0",
            ),
            BackendInfo(
                id="networkx-kl",
                name="NetworkX Kernighan-Lin",
                package="networkx",
                optional=False,
                available=True,
                version="3.0",
            ),
        ),
    )

    report = build_doctor_report(full=True)

    assert report["portfolio_ready"] is True
    assert report["portfolio_kway_ready"] is True
    assert report["portfolio_kway_backends"] == ["bloc", "metis"]


def test_doctor_kway_fields_are_declared_by_schema():
    import json
    from pathlib import Path

    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "atof-doctor-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    properties = schema["properties"]
    assert properties["portfolio_kway_ready"]["type"] == "boolean"
    assert properties["portfolio_kway_backends"]["type"] == "array"


def test_ai_manifest_validates_against_json_schema(capsys):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator
    from atof.cli import main

    assert main(["ai"]) == 0
    instance = json.loads(capsys.readouterr().out)
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "atof-ai-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(instance)


def test_doctor_report_validates_against_json_schema(capsys):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator
    from atof.cli import main

    assert main(["doctor"]) == 0
    instance = json.loads(capsys.readouterr().out)
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "atof-doctor-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(instance)


def test_doctor_readiness_excludes_installed_but_unimportable_backend(monkeypatch):
    from atof.backends import inspect_backends

    real_import = __import__("importlib").import_module

    def fake_import(name):
        if name == "pymetis":
            raise OSError("native library unavailable")
        return real_import(name)

    monkeypatch.setattr("atof.backends.importlib.import_module", fake_import)

    def fake_version(name):
        return "test-version" if name == "pymetis" else None

    monkeypatch.setattr("atof.backends.package_version", fake_version)

    backends = inspect_backends()
    metis = next(item for item in backends if item.id == "metis")

    assert metis.available is True
    assert metis.importable is False
    assert "native library unavailable" in metis.import_error
    assert metis.error == "package installed but import failed"


def test_doctor_schema_declares_importability_fields():
    import json
    from pathlib import Path

    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "atof-doctor-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    backend_schema = schema["properties"]["backends"]["items"]
    assert "importable" in backend_schema["properties"]
    assert "import_error" in backend_schema["properties"]


def test_doctor_operational_probe_reports_backend_execution(monkeypatch):

    class FakeCandidate:
        def __init__(self, backend_id, ok, error=None):
            self.id = backend_id
            self.available = ok
            self.partition = {0: 0, 1: 1} if ok else None
            self.edge_cut = 1 if ok else None
            self.balance_error = 0.0 if ok else None
            self.runtime_seconds = 0.01 if ok else 0.0
            self.error = error

    class FakeResult:
        candidates = (
            FakeCandidate("bloc", True),
            FakeCandidate("metis", False, "native failure"),
        )

    monkeypatch.setattr("atof.ai.inspect_backends", lambda: ())
    monkeypatch.setattr("atof.ai.optimize_portfolio", lambda *args, **kwargs: FakeResult())

    report = build_doctor_report(full=True, probe=True)

    assert report["probe"]["requested"] is True
    assert report["probe"]["k"] == 2
    assert report["probe"]["graph"] == {"nodes": 8, "edges": 7}
    assert report["probe"]["backends"]["bloc"]["ok"] is True
    assert report["probe"]["backends"]["metis"]["ok"] is False
    assert report["probe"]["backends"]["metis"]["error"] == "native failure"


def test_doctor_probe_payload_validates_against_schema(monkeypatch):
    import json
    from jsonschema import Draft202012Validator
    from pathlib import Path

    monkeypatch.setattr("atof.ai.inspect_backends", lambda: ())
    class FakeResult:
        candidates = ()
    monkeypatch.setattr("atof.ai.optimize_portfolio", lambda *args, **kwargs: FakeResult())

    payload = build_doctor_report(full=True, probe=True)
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "atof-doctor-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(payload)


def test_doctor_probe_reports_global_failure_without_raising(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("all backends failed")

    monkeypatch.setattr("atof.ai.inspect_backends", lambda: ())
    monkeypatch.setattr("atof.ai.optimize_portfolio", fail)

    report = build_doctor_report(full=True, probe=True)

    assert report["probe"]["requested"] is True
    assert report["probe"]["ok"] is False
    assert report["probe"]["backends"] == {}
    assert report["probe"]["error"] == "RuntimeError: all backends failed"


def test_ai_manifest_exposes_optional_probe_flag(capsys):
    from atof.cli import main
    import json

    assert main(["ai"]) == 0
    manifest = json.loads(capsys.readouterr().out)

    assert manifest["commands"]["doctor"] == "atof doctor"
    assert manifest["commands"]["short_flags"]["probe"] == "--probe"
