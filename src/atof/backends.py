from __future__ import annotations

from dataclasses import asdict, dataclass

from .provenance import package_version


@dataclass(frozen=True)
class BackendInfo:
    id: str
    name: str
    package: str
    optional: bool
    available: bool
    version: str | None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_SPECS = (
    ("bloc", "BLOC-RELOC", "atof", False),
    ("networkx-kl", "NetworkX Kernighan-Lin", "networkx", False),
    ("metis", "METIS via PyMetis", "pymetis", True),
    ("kahip", "KaHIP via KaFFPa-Strong", "kahip", True),
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
                    error="package not installed",
                )
            )
            continue
        results.append(
            BackendInfo(
                id=backend_id,
                name=name,
                package=package,
                optional=optional,
                available=True,
                version=version,
            )
        )
    return tuple(results)
