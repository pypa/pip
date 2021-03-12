import collections
import logging
from functools import partial
from typing import Iterator, List, Optional, Sequence, Tuple, Union

from pip._internal.utils.logging import indent_log
from pip._internal.utils.parallel import map_multiprocess_ordered

from .req_file import parse_requirements
from .req_install import InstallRequirement
from .req_set import RequirementSet

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


_InstallArgs = collections.namedtuple(
    '_InstallArgs',
    ['install_options', 'global_options', 'kwargs']
)


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
    installed = []  # type: List[InstallationResult]

    # store install arguments
    install_args = _InstallArgs(
        install_options=install_options,
        global_options=global_options,
        kwargs=dict(
            root=root, home=home, prefix=prefix,
            warn_script_location=warn_script_location,
            use_user_site=use_user_site, pycompile=pycompile
        )
    )

    with indent_log():
        # first try to install in parallel
        installed_pool = map_multiprocess_ordered(
            partial(_single_install, install_args, in_subprocess=True),
            requirements)

        # check the results from the parallel installation,
        # and fill-in missing installations or raise exception
        for installed_req, requested_req in zip(installed_pool, requirements):
            # if the requirement was not installed by the parallel pool,
            # install serially here
            if installed_req is None:
                installed_req = _single_install(
                    install_args, requested_req, in_subprocess=False)

            if isinstance(installed_req, BaseException):
                # Raise an exception if we caught one
                # during the parallel installation
                raise installed_req
            elif isinstance(installed_req, InstallationResult):
                installed.append(installed_req)

    return installed


def _single_install(
        install_args,           # type: _InstallArgs
        requirement,            # type: InstallRequirement
        in_subprocess=False,    # type: bool
):
    # type: (...) -> Union[None, InstallationResult, BaseException]
    """
    Install a single requirement, returns InstallationResult
    (to be called per requirement, either in parallel or serially)
    """

    # if we are running inside a subprocess,
    # then only clean wheel installation is supported
    if (in_subprocess and
            (requirement.should_reinstall or not requirement.is_wheel)):
        return None

    if requirement.should_reinstall:
        logger.info('Attempting uninstall: %s', requirement.name)
        with indent_log():
            uninstalled_pathset = requirement.uninstall(
                auto_confirm=True
            )
    else:
        uninstalled_pathset = None

    try:
        requirement.install(
            install_args.install_options,
            install_args.global_options,
            **install_args.kwargs
        )
    except (KeyboardInterrupt, SystemExit):
        # always raise, we catch it in external loop
        raise
    except BaseException as ex:
        # if install did not succeed, rollback previous uninstall
        if uninstalled_pathset and not requirement.install_succeeded:
            uninstalled_pathset.rollback()
        if in_subprocess:
            return ex
        raise

    if uninstalled_pathset and requirement.install_succeeded:
        uninstalled_pathset.commit()

    return InstallationResult(requirement.name or '')
