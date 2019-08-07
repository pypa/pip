"""Contains the RequirementCommand base class.

This is in a separate module so that Command classes not inheriting from
RequirementCommand don't need to import e.g. the PackageFinder machinery
and all its vendored dependencies.
"""

from pip._internal.cli.base_command import Command
from pip._internal.cli.cmdoptions import make_search_scope
from pip._internal.exceptions import CommandError
from pip._internal.index import PackageFinder
from pip._internal.legacy_resolve import Resolver
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._internal.req.req_file import parse_requirements
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from optparse import Values
    from typing import List, Optional, Tuple
    from pip._internal.cache import WheelCache
    from pip._internal.download import PipSession
    from pip._internal.models.target_python import TargetPython
    from pip._internal.req.req_set import RequirementSet
    from pip._internal.req.req_tracker import RequirementTracker
    from pip._internal.utils.temp_dir import TempDirectory


class RequirementCommand(Command):

    @staticmethod
    def make_requirement_preparer(
            temp_directory,           # type: TempDirectory
            options,                  # type: Values
            req_tracker,              # type: RequirementTracker
            download_dir=None,        # type: str
            wheel_download_dir=None,  # type: str
    ):
        # type: (...) -> RequirementPreparer
        """
        Create a RequirementPreparer instance for the given parameters.
        """
        return RequirementPreparer(
            build_dir=temp_directory.path,
            src_dir=options.src_dir,
            download_dir=download_dir,
            wheel_download_dir=wheel_download_dir,
            progress_bar=options.progress_bar,
            build_isolation=options.build_isolation,
            req_tracker=req_tracker,
        )

    @staticmethod
    def make_resolver(
            preparer,                            # type: RequirementPreparer
            session,                             # type: PipSession
            finder,                              # type: PackageFinder
            options,                             # type: Values
            wheel_cache=None,                    # type: Optional[WheelCache]
            use_user_site=False,                 # type: bool
            ignore_installed=True,               # type: bool
            ignore_requires_python=False,        # type: bool
            force_reinstall=False,               # type: bool
            upgrade_strategy="to-satisfy-only",  # type: str
            use_pep517=None,                     # type: Optional[bool]
            py_version_info=None            # type: Optional[Tuple[int, ...]]
    ):
        # type: (...) -> Resolver
        """
        Create a Resolver instance for the given parameters.
        """
        return Resolver(
            preparer=preparer,
            session=session,
            finder=finder,
            wheel_cache=wheel_cache,
            use_user_site=use_user_site,
            ignore_dependencies=options.ignore_dependencies,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            force_reinstall=force_reinstall,
            isolated=options.isolated_mode,
            upgrade_strategy=upgrade_strategy,
            use_pep517=use_pep517,
            py_version_info=py_version_info
        )

    @staticmethod
    def populate_requirement_set(requirement_set,  # type: RequirementSet
                                 args,             # type: List[str]
                                 options,          # type: Values
                                 finder,           # type: PackageFinder
                                 session,          # type: PipSession
                                 name,             # type: str
                                 wheel_cache       # type: Optional[WheelCache]
                                 ):
        # type: (...) -> None
        """
        Marshal cmd line args into a requirement set.
        """
        # NOTE: As a side-effect, options.require_hashes and
        #       requirement_set.require_hashes may be updated

        for filename in options.constraints:
            for req_to_add in parse_requirements(
                    filename,
                    constraint=True, finder=finder, options=options,
                    session=session, wheel_cache=wheel_cache):
                req_to_add.is_direct = True
                requirement_set.add_requirement(req_to_add)

        for req in args:
            req_to_add = install_req_from_line(
                req, None, isolated=options.isolated_mode,
                use_pep517=options.use_pep517,
                wheel_cache=wheel_cache
            )
            req_to_add.is_direct = True
            requirement_set.add_requirement(req_to_add)

        for req in options.editables:
            req_to_add = install_req_from_editable(
                req,
                isolated=options.isolated_mode,
                use_pep517=options.use_pep517,
                wheel_cache=wheel_cache
            )
            req_to_add.is_direct = True
            requirement_set.add_requirement(req_to_add)

        for filename in options.requirements:
            for req_to_add in parse_requirements(
                    filename,
                    finder=finder, options=options, session=session,
                    wheel_cache=wheel_cache,
                    use_pep517=options.use_pep517):
                req_to_add.is_direct = True
                requirement_set.add_requirement(req_to_add)
        # If --require-hashes was a line in a requirements file, tell
        # RequirementSet about it:
        requirement_set.require_hashes = options.require_hashes

        if not (args or options.editables or options.requirements):
            opts = {'name': name}
            if options.find_links:
                raise CommandError(
                    'You must give at least one requirement to %(name)s '
                    '(maybe you meant "pip %(name)s %(links)s"?)' %
                    dict(opts, links=' '.join(options.find_links)))
            else:
                raise CommandError(
                    'You must give at least one requirement to %(name)s '
                    '(see "pip help %(name)s")' % opts)

    def _build_package_finder(
        self,
        options,               # type: Values
        session,               # type: PipSession
        target_python=None,    # type: Optional[TargetPython]
        ignore_requires_python=None,  # type: Optional[bool]
    ):
        # type: (...) -> PackageFinder
        """
        Create a package finder appropriate to this requirement command.

        :param ignore_requires_python: Whether to ignore incompatible
            "Requires-Python" values in links. Defaults to False.
        """
        search_scope = make_search_scope(options)
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            format_control=options.format_control,
            allow_all_prereleases=options.pre,
            prefer_binary=options.prefer_binary,
            ignore_requires_python=ignore_requires_python,
        )

        return PackageFinder.create(
            search_scope=search_scope,
            selection_prefs=selection_prefs,
            trusted_hosts=options.trusted_hosts,
            session=session,
            target_python=target_python,
        )
