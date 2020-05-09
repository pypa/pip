import collections
import logging
from typing import Iterator, List, Optional, Sequence, Tuple

from pip._internal.utils.logging import indent_log
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .req_file import parse_requirements
from .req_install import InstallRequirement
from .req_set import RequirementSet

try:
    from multiprocessing.pool import Pool
except ImportError:  # Platform-specific: No multiprocessing available
    Pool = None

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
    installed = [None] * len(to_install)
    install_args = [install_options, global_options, dict(
    	root=root, home=home, prefix=prefix, warn_script_location=warn_script_location,
    	use_user_site=use_user_site, pycompile=pycompile)]

    if Pool is not None:
        # first let's try to install in parallel, if we fail we do it by order.
        pool = Pool()
        try:
            pool_result = pool.starmap_async(__single_install, [(install_args, r) for r in to_install])
            # python 2.7 timeout=None will not catch KeyboardInterrupt
            installed = pool_result.get(timeout=999999)
        except (KeyboardInterrupt, SystemExit):
            pool.terminate()
            raise
        except Exception:
            # we will reinstall sequentially
            pass
        pool.close()
        pool.join()

    with indent_log():
        for i, requirement in enumerate(to_install):
            if installed[i] is None:
                installed[i] = __single_install(install_args, requirement, allow_raise=True)

    return [i for i in installed if i is not None]


def __single_install(args, a_requirement, allow_raise=False):
    if a_requirement.should_reinstall:
        logger.info('Attempting uninstall: %s', a_requirement.name)
        with indent_log():
            uninstalled_pathset = a_requirement.uninstall(
                auto_confirm=True
            )
    try:
        a_requirement.install(
            args[0],   # install_options,
            args[1],   # global_options,
            **args[2]  # **kwargs
        )
    except Exception:
        should_rollback = (
                a_requirement.should_reinstall and
                not a_requirement.install_succeeded
        )
        # if install did not succeed, rollback previous uninstall
        if should_rollback:
            uninstalled_pathset.rollback()
        if allow_raise:
            raise
    else:
        should_commit = (
                a_requirement.should_reinstall and
                a_requirement.install_succeeded
        )
        if should_commit:
            uninstalled_pathset.commit()
        return InstallationResult(a_requirement.name)

    return None
