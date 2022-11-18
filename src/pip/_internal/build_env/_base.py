import logging
import os
import pathlib
from typing import TYPE_CHECKING, Iterable

from pip import __file__ as pip_location
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
