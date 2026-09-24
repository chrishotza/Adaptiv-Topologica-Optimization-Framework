from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib

from .provenance import package_version


@dataclass(frozen=True)
class BackendInfo:
    id: str
    name: str
    package: str
    optional: bool
    available: bool
    version: str | None
    importable: bool = False
    import_error: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_SPECS = (
    ("bloc", "BLOC-RELOC", "atof", False),
    ("networkx-kl", "NetworkX Kernighan-Lin", "networkx", False),
    ("metis", "METIS via PyMetis", "pymetis", True),
    ("kahip", "KaHIP via KaFFPa-Strong", "kahip", True),
    ("kaminpar", "KaMinPar default", "kaminpar", True),
    ("kaminpar-strong", "KaMinPar strong", "kaminpar", True),
    ("mtkahypar", "Mt-KaHyPar default", "mtkahypar", True),
    ("mtkahypar-quality", "Mt-KaHyPar quality", "mtkahypar", True),
)


def inspect_backends(*, include_optional: bool = True) -> tuple[BackendInfo, ...]:
    results: list[BackendInfo] = []
    for backend_id, name, package, optional in _SPECS:
        if optional and not include_optional:
            continue
        version = package_version(package)
        if version is None:
            results.append(
                BackendInfo(
                    id=backend_id,
                    name=name,
                    package=package,
                    optional=optional,
                    available=False,
                    version=None,
                    importable=False,
                    import_error=None,
                    error="package not installed",
                )
            )
            continue

        try:
            importlib.import_module(package)
        except Exception as exc:
            results.append(
                BackendInfo(
                    id=backend_id,
                    name=name,
                    package=package,
                    optional=optional,
                    available=True,
                    version=version,
                    importable=False,
                    import_error=f"{type(exc).__name__}: {exc}",
                    error="package installed but import failed",
                )
            )
        else:
            results.append(
                BackendInfo(
                    id=backend_id,
                    name=name,
                    package=package,
                    optional=optional,
                    available=True,
                    version=version,
                    importable=True,
                    import_error=None,
                )
            )
    return tuple(results)
