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
