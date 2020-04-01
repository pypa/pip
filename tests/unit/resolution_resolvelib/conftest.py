from functools import partial

import pytest

from pip._internal.cli.req_command import RequirementCommand
from pip._internal.commands.install import InstallCommand
from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
# from pip._internal.models.index import PyPI
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.network.session import PipSession
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.req.req_tracker import get_requirement_tracker
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.utils.temp_dir import TempDirectory, global_tempdir_manager


@pytest.fixture
def finder(data):
    session = PipSession()
    scope = SearchScope([str(data.packages)], [])
    collector = LinkCollector(session, scope)
    prefs = SelectionPreferences(allow_yanked=False)
    finder = PackageFinder.create(collector, prefs)
    yield finder


@pytest.fixture
def preparer(finder):
    session = PipSession()
    rc = InstallCommand("x", "y")
    o = rc.parse_args([])

    with global_tempdir_manager():
        with TempDirectory() as tmp:
            with get_requirement_tracker() as tracker:
                preparer = RequirementCommand.make_requirement_preparer(
                    tmp,
                    options=o[0],
                    req_tracker=tracker,
                    session=session,
                    finder=finder,
                    use_user_site=False
                )

                yield preparer


@pytest.fixture
def factory(finder, preparer):
    make_install_req = partial(
        install_req_from_req_string,
        isolated=False,
        use_pep517=None,
    )
    yield Factory(
        finder=finder,
        preparer=preparer,
        make_install_req=make_install_req,
    )


@pytest.fixture
def provider(factory):
    yield PipProvider(
        factory=factory,
        ignore_dependencies=False,
    )
