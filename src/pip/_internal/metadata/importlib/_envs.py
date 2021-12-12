import importlib.metadata
import pathlib
import sys
from typing import Iterator, List, Optional, Sequence, Set

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.metadata.base import BaseDistribution, BaseEnvironment

from ._compat import BasePath, get_dist_normalized_name, get_info_location
from ._dists import Distribution


class _DistributionFinder:
    """Finder to locate distributions.

    The main purpose of this class is to memoize found distributions' names, so
    only one distribution is returned for each package name. At lot of pip code
    assumes this (because it is setuptools's behavior), and not doing the same
    can potentially cause a distribution in lower precedence path to override a
    higher precedence one if the caller is not careful.

    Eventually we probably want to make it possible to see lower precedence
    installations as well. It's useful feature, after all.
    """

    Distributions = Iterator[BaseDistribution]

    def __init__(self):
        self._found_names: Set[NormalizedName] = set()

    def _find_impl(self, path: pathlib.Path, source: BasePath) -> Distributions:
        """Find distributions in a location."""
        # To know exact where we found a distribution, we have to feed the paths
        # in one by one, instead of dumping entire list to importlib.metadata.
        for dist in importlib.metadata.distributions(path=[str(path)]):
            normalized_name = get_dist_normalized_name(dist)
            if normalized_name in self._found_names:
                continue
            self._found_names.add(normalized_name)
            info_location = get_info_location(dist)
            yield Distribution(dist, path, info_location, source)

    def find_in(self, path: pathlib.Path) -> Distributions:
        """Find distributions in a location.

        The path can be either a directory, or a ZIP archive.
        """
        yield from self._find_impl(path, source=path)


class Environment(BaseEnvironment):
    def __init__(self, paths: Sequence[str]) -> None:
        self._paths = paths

    @classmethod
    def default(cls) -> BaseEnvironment:
        return cls(sys.path)

    @classmethod
    def from_paths(cls, paths: Optional[List[str]]) -> BaseEnvironment:
        if paths is None:
            return cls(sys.path)
        return cls(paths)

    def _iter_distributions(self) -> Iterator[BaseDistribution]:
        finder = _DistributionFinder()
        for location in self._paths:
            yield from finder.find_in(pathlib.Path(location))

    def get_distribution(self, name: str) -> Optional[BaseDistribution]:
        matches = (
            distribution
            for distribution in self.iter_all_distributions()
            if distribution.canonical_name == canonicalize_name(name)
        )
        return next(matches, None)
