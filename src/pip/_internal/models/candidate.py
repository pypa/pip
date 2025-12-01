from dataclasses import dataclass
from typing import Optional, Set

from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.models.link import Link


@dataclass(frozen=True)
class InstallationCandidate:
    """Represents a potential "candidate" for installation."""

    __slots__ = ["name", "version", "link"]

    name: str
    version: Version
    link: Link

    def __init__(self, name: str, version: str, link: Link) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", parse_version(version))
        object.__setattr__(self, "link", link)

    def __str__(self) -> str:
        return f"{self.name!r} candidate (version {self.version} at {self.link})"


@dataclass(frozen=True)
class RemoteInstallationCandidate:
    """Represents a potential "candidate" for installation."""

    __slots__ = ["canonical_name", "candidate"]

    canonical_name: str
    candidate: InstallationCandidate

    def __init__(self, canonical_name: str, candidate: InstallationCandidate) -> None:
        object.__setattr__(self, "canonical_name", canonical_name)
        object.__setattr__(self, "candidate", candidate)

    def __str__(self) -> str:
        return f"{self.canonical_name!r} candidate"

    @property
    def _link(self) -> Optional[Link]:
        if not self.candidate:
            return None
        if not self.candidate.link:
            return None
        return self.candidate.link

    @property
    def url(self) -> Optional[str]:
        """The remote url that contains the metadata for this installation candidate."""
        link = self._link
        if not link:
            return None
        cf = link.comes_from
        if cf is None:
            return None
        url_attr = getattr(cf, "url", None)
        if isinstance(url_attr, str):
            return url_attr.lstrip()
        if isinstance(cf, str):
            return cf.lstrip()

        return None

    @property
    def remote_repository_urls(self) -> Set[str]:
        """Remote repository urls from Tracks and Alternate Locations metadata."""
        return {*self.project_track_urls, *self.alternate_location_urls}

    @property
    def project_track_urls(self) -> Set[str]:
        """Remote repository urls from Tracks metadata."""
        link = self._link
        if not link or not link.project_track_urls:
            return set()
        return {i for i in link.project_track_urls if i}

    @property
    def alternate_location_urls(self) -> Set[str]:
        """Remote repository urls from Alternate Locations metadata."""
        urls: Set[str] = set()
        if self.url:
            urls.add(self.url)
        link = self._link
        if link and link.repo_alt_urls:
            urls.update({i for i in link.repo_alt_urls if i})
        return urls
