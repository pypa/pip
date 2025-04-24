import os

from pip._internal.vcs.mercurial import Mercurial

from tests.lib import PipTestEnvironment, _create_test_package, need_mercurial


@need_mercurial
def test_get_repository_root(script: PipTestEnvironment) -> None:
    version_pkg_path = _create_test_package(script.scratch_path, vcs="hg")
    tests_path = version_pkg_path.joinpath("tests")
    tests_path.mkdir()

    root1 = Mercurial.get_repository_root(os.fspath(version_pkg_path))
    assert root1 is not None
    assert os.path.normcase(root1) == os.path.normcase(version_pkg_path)

    root2 = Mercurial.get_repository_root(os.fspath(tests_path))
    assert root2 is not None
    assert os.path.normcase(root2) == os.path.normcase(version_pkg_path)
