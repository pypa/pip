import email.message
import importlib.metadata
import os
import pathlib
import sys
import zipfile
from typing import (
    Collection,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import InvalidWheel, UnsupportedWheel
from pip._internal.utils.wheel import parse_wheel, read_wheel_metadata_file

from .base import (
    BaseDistribution,
    BaseEntryPoint,
    BaseEnvironment,
    DistributionVersion,
    InfoPath,
    Wheel,
)


class BasePath(Protocol):
    """A protocol that various path objects conform.

    This exists because importlib.metadata uses both ``pathlib.Path`` and
    ``zipfile.Path``, and we need a common base for type hints (Union does not
    work well since ``zipfile.Path`` is too new for our linter setup).

    This does not mean to be exhaustive, but only contains things that present
    in both classes *that we need*.
    """

    name: str


class WheelDistribution(importlib.metadata.Distribution):
    """Distribution read from a wheel.

    Although ``importlib.metadata.PathDistribution`` accepts ``zipfile.Path``,
    its implementation is too "lazy" for pip's needs (we can't keep the ZipFile
    handle open for the entire lifetime of the distribution object).

    This implementation eagerly reads the entire metadata directory into the
    memory instead, and operates from that.
    """

    def __init__(
        self,
        files: Mapping[pathlib.PurePosixPath, bytes],
        info_location: pathlib.PurePosixPath,
    ) -> None:
        self._files = files
        self.info_location = info_location

    @classmethod
    def from_zipfile(
        cls,
        zf: zipfile.ZipFile,
        name: str,
        location: str,
    ) -> "WheelDistribution":
        info_dir, _ = parse_wheel(zf, name)
        paths = (
            (name, pathlib.PurePosixPath(name.split("/", 1)[-1]))
            for name in zf.namelist()
            if name.startswith(f"{info_dir}/")
        )
        files = {
            relpath: read_wheel_metadata_file(zf, fullpath)
            for fullpath, relpath in paths
        }
        info_location = pathlib.PurePosixPath(location, info_dir)
        return cls(files, info_location)

    def iterdir(self, path: InfoPath) -> Iterator[pathlib.PurePosixPath]:
        # Only allow iterating through the metadata directory.
        if pathlib.PurePosixPath(str(path)) in self._files:
            return iter(self._files)
        raise FileNotFoundError(path)

    def read_text(self, filename: str) -> Optional[str]:
        try:
            data = self._files[pathlib.PurePosixPath(filename)]
        except KeyError:
            return None
        return data.decode("utf-8")


class Distribution(BaseDistribution):
    def __init__(
        self,
        dist: importlib.metadata.Distribution,
        location: BasePath,
        info_location: Optional[BasePath],
    ) -> None:
        self._dist = dist
        self._location = location
        self._info_location = info_location

    @classmethod
    def from_directory(cls, directory: str) -> BaseDistribution:
        info_location = pathlib.Path(directory)
        dist = importlib.metadata.Distribution.at(info_location)
        location = info_location.parent
        return cls(dist, location, info_location)

    @classmethod
    def from_wheel(cls, wheel: Wheel, name: str) -> BaseDistribution:
        try:
            with wheel.as_zipfile() as zf:
                dist = WheelDistribution.from_zipfile(zf, name, wheel.location)
        except zipfile.BadZipFile as e:
            raise InvalidWheel(wheel.location, name) from e
        except UnsupportedWheel as e:
            raise UnsupportedWheel(f"{name} has an invalid wheel, {e}")
        return cls(dist, pathlib.PurePosixPath(wheel.location), dist.info_location)

    @property
    def location(self) -> Optional[str]:
        return str(self._location)

    @property
    def info_location(self) -> Optional[str]:
        if self._info_location is None:
            return None
        return str(self._info_location)

    def _get_dist_normalized_name(self) -> NormalizedName:
        # The 'name' attribute is only available in Python 3.10 or later. We are
        # only targeting that, but Mypy does not know this.
        return canonicalize_name(self._dist.name)  # type: ignore[attr-defined]

    @property
    def canonical_name(self) -> NormalizedName:
        # Try to get the name from the metadata directory name. This is much
        # faster than reading metadata.
        if self._info_location is None:
            return self._get_dist_normalized_name()
        stem, suffix = os.path.splitext(self._info_location.name)
        if suffix not in (".dist-info", ".egg-info"):
            return self._get_dist_normalized_name()
        name, _, _ = stem.partition("-")
        return canonicalize_name(name)

    @property
    def version(self) -> DistributionVersion:
        return parse_version(self._dist.version)

    def is_file(self, path: InfoPath) -> bool:
        return self._dist.read_text(str(path)) is not None

    def iter_distutils_script_names(self) -> Iterator[str]:
        if not isinstance(self._info_location, pathlib.Path):
            return
        for child in self._info_location.joinpath("scripts").iterdir():
            yield child.name

    def read_text(self, path: InfoPath) -> str:
        content = self._dist.read_text(str(path))
        if content is None:
            raise FileNotFoundError(path)
        return content

    def iter_entry_points(self) -> Iterable[BaseEntryPoint]:
        # importlib.metadata's EntryPoint structure sasitfies BaseEntryPoint.
        return self._dist.entry_points

    @property
    def metadata(self) -> email.message.Message:
        return self._dist.metadata

    def iter_dependencies(self, extras: Collection[str] = ()) -> Iterable[Requirement]:
        requires = self._dist.requires
        if requires is None:
            return
        for r in requires:
            req = Requirement(r)
            if not req.marker:
                yield req
            elif any(req.marker.evaluate({"extra": extra}) for extra in extras):
                yield req

    def _iter_egg_info_extras(self) -> Iterable[str]:
        """Parse extras from an .egg-info directory.

        An .egg-info directory stores dependencies in an INI-like file named
        ``requires.txt``, with extras being a part of the section names.
        """
        requires_txt = self._dist.read_text("requires.txt")
        if requires_txt is None:
            return
        for line in requires_txt.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                yield line.strip("[]").partition(":")[0]

    def iter_provided_extras(self) -> Iterable[str]:
        return (
            self._dist.metadata.get_all("Provides-Extra")
            or self._iter_egg_info_extras()
        )


def _get_info_location(d: importlib.metadata.Distribution) -> Optional[BasePath]:
    """Find the path to the distribution's metadata directory.

    HACK: This relies on importlib.metadata's private ``_path`` attribute. Not
    all distributions exist on disk, so importlib.metadata is correct to not
    expose the attribute as public. But pip's code base is old and not as clean,
    so we do this to avoid having to rewrite too many things. Hopefully we can
    eliminate this some day.
    """
    return getattr(d, "_path", None)


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
        # To know exact where we found a distribution, we have to feed the paths
        # in one by one, instead of dumping entire list to importlib.metadata.
        for path in self._paths:
            for dist in importlib.metadata.distributions(path=[path]):
                location = pathlib.Path(path)
                info_location = _get_info_location(dist)
                yield Distribution(dist, location, info_location)

    def get_distribution(self, name: str) -> Optional[BaseDistribution]:
        matches = (
            distribution
            for distribution in self._iter_distributions()
            if distribution.canonical_name == canonicalize_name(name)
        )
        return next(matches, None)
