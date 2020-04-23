from pip._vendor import pkg_resources
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.misc import dist_in_usersite, dist_is_editable, dist_is_local
from pip._internal.utils.packaging import get_installer
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import BaseDistribution, BaseEnvironment

if MYPY_CHECK_RUNNING:
    from typing import Iterator, List, Optional


class Distribution(BaseDistribution):
    def __init__(self, dist):
        # type: (pkg_resources.Distribution) -> None
        self._dist = dist

    @property
    def canonical_name(self):
        # type: () -> str
        return canonicalize_name(self._dist.project_name)

    @property
    def installer(self):
        # type: () -> str
        return get_installer(self._dist)

    @property
    def editable(self):
        # type: () -> bool
        return dist_is_editable(self._dist)

    @property
    def local(self):
        # type: () -> bool
        return dist_is_local(self._dist)

    @property
    def in_usersite(self):
        # type: () -> bool
        return dist_in_usersite(self._dist)


class Environment(BaseEnvironment):
    def __init__(self, ws):
        # type: (pkg_resources.WorkingSet) -> None
        self._ws = ws

    @classmethod
    def default(cls):
        # type: () -> BaseEnvironment
        return cls(pkg_resources.working_set)

    @classmethod
    def from_paths(cls, paths):
        # type: (List[str]) -> BaseEnvironment
        return cls(pkg_resources.WorkingSet(paths))

    def get_distribution(self, name):
        # type: (str) -> Optional[BaseDistribution]
        req = pkg_resources.Requirement(name)
        try:
            dist = self._ws.find(req)
        except pkg_resources.DistributionNotFound:
            return None
        return Distribution(dist)

    def iter_distributions(self):
        # type: () -> Iterator[BaseDistribution]
        for dist in self._ws:
            yield Distribution(dist)
