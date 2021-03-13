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
    ['install_options', 'global_options', 'root', 'home', 'prefix',
     'warn_script_location', 'use_user_site', 'pycompile']
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
        root=root,
        home=home,
        prefix=prefix,
        warn_script_location=warn_script_location,
        use_user_site=use_user_site,
        pycompile=pycompile,
    )

    with indent_log():
        # get a list of packages we can install in parallel
        should_parallel_reqs = [
            (i, req) for i, req in enumerate(requirements)
            if not req.should_reinstall and req.is_wheel
        ]

        if should_parallel_reqs:
            # install packages in parallel
            should_parallel_indexes, should_parallel_values = zip(
                *should_parallel_reqs)
            parallel_reqs_dict = dict(
                zip(should_parallel_indexes,
                    map_multiprocess_ordered(
                        partial(_single_install,
                                install_args,
                                suppress_exception=True),
                        should_parallel_values)))
        else:
            parallel_reqs_dict = {}

        # check the results from the parallel installation,
        # and fill-in missing installations or raise exception
        for i, req in enumerate(requirements):

            # select the install result from the parallel installation
            # or install serially now
            try:
                installed_req = parallel_reqs_dict[i]
            except KeyError:
                installed_req = _single_install(
                    install_args, req, suppress_exception=False)

            # Now processes the installation result,
            # throw exception or add into installed packages
            if isinstance(installed_req, BaseException):
                # Raise an exception if we caught one
                # during the parallel installation
                raise installed_req
            elif isinstance(installed_req, InstallationResult):
                installed.append(installed_req)

    return installed


def _single_install(
        install_args,                # type: _InstallArgs
        requirement,                 # type: InstallRequirement
        suppress_exception=False,    # type: bool
):
    # type: (...) -> Union[None, InstallationResult, BaseException]
    """
    Install a single requirement, returns InstallationResult
    (to be called per requirement, either in parallel or serially).
    Notice the two lists are of the same length
    """

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
            **install_args._asdict()
        )
    except Exception as ex:
        # Notice we might need to catch BaseException as this function
        # can be executed from a subprocess.
        # For the time being we keep the original catch Exception

        # if install did not succeed, rollback previous uninstall
        if uninstalled_pathset and not requirement.install_succeeded:
            uninstalled_pathset.rollback()
        if suppress_exception:
            return ex
        raise

    if uninstalled_pathset and requirement.install_succeeded:
        uninstalled_pathset.commit()

    return InstallationResult(requirement.name or '')
