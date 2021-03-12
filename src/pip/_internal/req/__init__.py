import collections
import logging
import sys
from functools import partial
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from ..._internal.utils.logging import indent_log
from .req_file import parse_requirements
from .req_install import InstallRequirement
from .req_set import RequirementSet

try:
    from multiprocessing.pool import Pool  # noqa
except ImportError:  # Platform-specific: No multiprocessing available
    Pool = None   # type: ignore

__all__ = [
    "RequirementSet", "InstallRequirement",
    "parse_requirements", "install_given_reqs",
]

logger = logging.getLogger(__name__)


class InstallationResult:
    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def __repr__(self):
        # type: () -> str
        return f"InstallationResult(name={self.name!r})"


def _validate_requirements(
    requirements,  # type: List[InstallRequirement]
):
    # type: (...) -> Iterator[Tuple[str, InstallRequirement]]
    for req in requirements:
        assert req.name, f"invalid to-be-installed requirement: {req}"
        yield req.name, req


def install_given_reqs(
    requirements,  # type: List[InstallRequirement]
    install_options,  # type: List[str]
    global_options,  # type: Sequence[str]
    root,  # type: Optional[str]
    home,  # type: Optional[str]
    prefix,  # type: Optional[str]
    warn_script_location,  # type: bool
    use_user_site,  # type: bool
    pycompile,  # type: bool
):
    # type: (...) -> List[InstallationResult]
    """
    Install everything in the given list.

    (to be called after having downloaded and unpacked the packages)
    """
    to_install = collections.OrderedDict(_validate_requirements(requirements))

    if to_install:
        logger.info(
            'Installing collected packages: %s',
            ', '.join(to_install.keys()),
        )

    # pre allocate installed package names
    installed = collections.OrderedDict({name: None for name in to_install})

    install_args = [install_options, global_options, dict(
        root=root, home=home, prefix=prefix,
        warn_script_location=warn_script_location,
        use_user_site=use_user_site, pycompile=pycompile)]

    with indent_log():
        # first try to install in parallel
        installed_pool = __safe_pool_map(
            partial(__single_install, install_args, in_subprocess=True),
            list(to_install.values()))
        if installed_pool:
            installed = collections.OrderedDict(
                zip(list(to_install.keys()), installed_pool))

        for name, requirement in to_install.items():
            if installed[name] is None:
                installed_req = __single_install(
                    install_args, requirement, in_subprocess=False)
                installed[name] = installed_req  # type: ignore
            elif isinstance(installed[name], BaseException):
                raise installed[name]   # type: ignore

    return [i for i in installed if isinstance(i, InstallationResult)]


def __safe_pool_map(
        func,               # type: Callable[[Any], Any]
        iterable,           # type: Iterable[Any]
):
    # type: (...) -> Optional[List[Any]]
    """
    Safe call to Pool map, if Pool is not available return None
    """
    # Disable multiprocessing on Windows python 2.7
    if sys.platform == 'win32' and sys.version_info.major == 2:
        return None

    if not iterable or Pool is None:
        return None

    # first let's try to install in parallel,
    # if we fail we do it by order.
    try:
        # Pool context would have been nice, but not supported on Python 2.7
        # Once officially dropped, switch to context to avoid close/join calls
        pool = Pool()
    except ImportError:
        return [func(i) for i in iterable]
    else:
        try:
            # python 2.7 timeout=None will not catch KeyboardInterrupt
            results = pool.map_async(func, iterable).get(timeout=999999)
        except (KeyboardInterrupt, SystemExit):
            pool.terminate()
            raise
        else:
            pool.close()
            pool.join()
            return results


def __single_install(
        install_args,           # type: List[Any]
        requirement,            # type: InstallRequirement
        in_subprocess=False,    # type: bool
):
    # type: (...) -> Union[None, InstallationResult, BaseException]
    """
    Install a single requirement, returns InstallationResult
    (to be called per requirement, either in parallel or serially)
    """
    if (in_subprocess and
            (requirement.should_reinstall or not requirement.is_wheel)):
        return None

    if requirement.should_reinstall:
        logger.info('Attempting uninstall: %s', requirement.name)
        with indent_log():
            uninstalled_pathset = requirement.uninstall(
                auto_confirm=True
            )
    try:
        requirement.install(
            install_args[0],   # install_options,
            install_args[1],   # global_options,
            **install_args[2]  # **kwargs
        )
    except (KeyboardInterrupt, SystemExit):
        # always raise, we catch it in external loop
        raise
    except BaseException as ex:
        should_rollback = (requirement.should_reinstall and
                           not requirement.install_succeeded)
        # if install did not succeed, rollback previous uninstall
        if should_rollback and uninstalled_pathset:
            uninstalled_pathset.rollback()
        if in_subprocess:
            return ex
        raise

    should_commit = (requirement.should_reinstall and
                     requirement.install_succeeded)
    if should_commit and uninstalled_pathset:
        uninstalled_pathset.commit()
    return InstallationResult(requirement.name or '')
