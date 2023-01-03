import abc
import logging
import os
import pathlib
from types import TracebackType
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Tuple, Type

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.logging import VERBOSE, getLogger

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = getLogger(__name__)


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


def iter_install_flags(finder: "PackageFinder") -> Iterable[str]:
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


class BuildEnvironment(metaclass=abc.ABCMeta):
    lib_dirs: List[str]

    def __init__(self) -> None:
        ...

    @abc.abstractmethod
    def __enter__(self) -> None:
        ...

    @abc.abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        ...

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        missing = set()
        conflicting = set()
        if reqs:
            env = (
                get_environment(self.lib_dirs)
                if self.lib_dirs
                else get_default_environment()
            )
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

    @abc.abstractmethod
    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()
