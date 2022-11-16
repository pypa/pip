import logging
import os
import pathlib
import sysconfig
import types
from typing import (
    TYPE_CHECKING,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.locations import get_prefixed_libs
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils._log import VERBOSE

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


class NoOpBuildEnvironment:
    """A build environment that does nothing."""

    _lib_dirs: Optional[List[str]] = None

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        pass

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        """Check if build requirements are satisfied in the environment.

        Returns 2 sets:

        - conflicting requirements: set of (installed, wanted) reqs tuples
        - missing requirements: set of reqs
        """
        missing = set()
        conflicting = set()
        if reqs:
            if self._lib_dirs is None:
                env = get_default_environment()
            else:
                env = get_environment(self._lib_dirs)
            for req_str in reqs:
                req = Requirement(req_str)
                # We're explicitly evaluating with an empty extra value, since build
                # environments are not provided any mechanism to select specific extras.
                if req.marker is not None and not req.marker.evaluate({"extra": ""}):
                    continue
                dist = env.get_distribution(req.name)
                if not dist:
                    missing.add(req_str)
                    continue
                if isinstance(dist.version, Version):
                    installed_req_str = f"{req.name}=={dist.version}"
                else:
                    installed_req_str = f"{req.name}==={dist.version}"
                if not req.specifier.contains(dist.version, prereleases=True):
                    conflicting.add((installed_req_str, req_str))
                # FIXME: Consider direct URL?
        return conflicting, missing

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Collection[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()


class OverlayBuildEnvironment(NoOpBuildEnvironment):
    _bin_dirs: List[str]
    _site_dir: Optional[str]
    _save_env: Dict[str, Optional[str]]

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name)
            for name in ("PATH", "PYTHONNOUSERSITE", "PYTHONPATH")
        }

        path = self._bin_dirs[:]
        old_path = self._save_env["PATH"]
        if old_path:
            path.extend(old_path.split(os.pathsep))

        os.environ.update({"PATH": os.pathsep.join(path), "PYTHONNOUSERSITE": "1"})
        if self._site_dir is not None:
            os.environ["PYTHONPATH"] = self._site_dir

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        for varname, old_value in self._save_env.items():
            if old_value is None:
                os.environ.pop(varname, None)
            else:
                os.environ[varname] = old_value


class Prefix:
    def __init__(self, path: str) -> None:
        self.path = path
        self.setup = False
        self.bin_dir = sysconfig.get_paths(
            "nt" if os.name == "nt" else "posix_prefix",
            vars={"base": path, "platbase": path},
        )["scripts"]
        self.lib_dirs = get_prefixed_libs(path)


def get_runnable_pip() -> str:
    """Get a file to pass to a Python executable, to run the currently-running pip.

    This is used to run a pip subprocess, for installing requirements into the build
    environment.
    """
    source = pathlib.Path(pip_location).resolve().parent

    if not source.is_dir():
        # This would happen if someone is using pip from inside a zip file. In that
        # case, we can use that directly.
        return str(source)

    return os.fsdecode(source / "__pip-runner__.py")


def iter_install_flags(finder: "PackageFinder") -> Iterator[str]:
    logging_level = logger.getEffectiveLevel()
    if logging_level <= logging.DEBUG:
        yield "-vv"
    elif logging_level <= VERBOSE:
        yield "-v"

    for format_control in ("no_binary", "only_binary"):
        formats = getattr(finder.format_control, format_control)
        format_control_key = format_control.replace("_", "-")
        yield f"--{format_control_key}"
        yield ",".join(sorted(formats)) or ":none:"

    index_urls = finder.index_urls
    if index_urls:
        yield "--index-url"
        yield index_urls[0]
        for extra_index in index_urls[1:]:
            yield "--extra-index-url"
            yield extra_index
    else:
        yield "--no-index"
    for link in finder.find_links:
        yield "--find-links"
        yield link

    for host in finder.trusted_hosts:
        yield "--trusted-host"
        yield host
    if finder.allow_all_prereleases:
        yield "--pre"
    if finder.prefer_binary:
        yield "--prefer-binary"
