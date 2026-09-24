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
