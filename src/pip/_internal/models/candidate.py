from dataclasses import dataclass
from typing import Optional

from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.models.link import Link


@dataclass(frozen=True)
class InstallationCandidate:
    """Represents a potential "candidate" for installation."""

    __slots__ = ["name", "version", "link", "variant_hash"]

    name: str
    version: Version
    link: Link
    variant_hash: Optional[str]

    def __init__(self, name: str, version: str, link: Link, variant_hash: Optional[str]) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", parse_version(version))
        object.__setattr__(self, "link", link)
        object.__setattr__(self, "variant_hash", variant_hash)

    def __str__(self) -> str:
        return f"{self.name!r} candidate (version {self.version} at {self.link}, variant hash: {self.variant_hash})"
