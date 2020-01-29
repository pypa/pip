import os
from os.path import exists

import pytest

from pip._internal.cli.status_codes import PREVIOUS_BUILD_DIR_ERROR
from pip._internal.utils.marker_files import write_delete_marker_file
from tests.lib import need_mercurial, windows_workaround_7667
from tests.lib.local_repos import local_checkout


def test_cleanup_after_install(script, data):
    """
    Test clean up after installing a package.
    """
    script.pip(
        'install', '--no-index',
        '--find-links={}'.format(data.find_links),
        'simple'
    )
    build = script.venv_path / "build"
    src = script.venv_path / "src"
    assert not exists(build), "build/ dir still exists: {}".format(build)
    assert not exists(src), "unexpected src/ dir exists: {}" .format(src)
    script.assert_no_temp()


@pytest.mark.network
def test_no_clean_option_blocks_cleaning_after_install(script, data):
    """
    Test --no-clean option blocks cleaning after install
    """
    build = script.base_path / 'pip-build'
    script.pip(
        'install', '--no-clean', '--no-index', '--build', build,
        '--find-links={}'.format(data.find_links), 'simple', expect_temp=True,
    )
    assert exists(build)


@pytest.mark.network
@need_mercurial
@windows_workaround_7667
def test_cleanup_after_install_editable_from_hg(script, tmpdir):
    """
    Test clean up after cloning from Mercurial.

    """
    requirement = '{}#egg=ScriptTest'.format(
        local_checkout('hg+https://bitbucket.org/ianb/scripttest', tmpdir)
    )
    script.pip('install', '-e', requirement)
    build = script.venv_path / 'build'
    src = script.venv_path / 'src'
    assert not exists(build), "build/ dir still exists: {}".format(build)
    assert exists(src), "expected src/ dir doesn't exist: {}".format(src)
    script.assert_no_temp()


def test_cleanup_after_install_from_local_directory(script, data):
    """
    Test clean up after installing from a local directory.
    """
    to_install = data.packages.joinpath("FSPkg")
    script.pip('install', to_install)
    build = script.venv_path / 'build'
    src = script.venv_path / 'src'
    assert not exists(build), "unexpected build/ dir exists: {}".format(build)
    assert not exists(src), "unexpected src/ dir exist: {}".format(src)
    script.assert_no_temp()


def test_cleanup_req_satisfied_no_name(script, data):
    """
    Test cleanup when req is already satisfied, and req has no 'name'
    """
    # this test confirms Issue #420 is fixed
    # reqs with no 'name' that were already satisfied were leaving behind tmp
    # build dirs
    # 2 examples of reqs that would do this
    # 1) https://bitbucket.org/ianb/initools/get/tip.zip
    # 2) parent-0.1.tar.gz
    dist = data.packages.joinpath("parent-0.1.tar.gz")

    script.pip('install', dist)
    script.pip('install', dist)

    build = script.venv_path / 'build'
    assert not exists(build), "unexpected build/ dir exists: %s" % build
    script.assert_no_temp()


def test_cleanup_after_install_exception(script, data):
    """
    Test clean up after a 'setup.py install' exception.
    """
    # broken==0.2broken fails during install; see packages readme file
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'broken==0.2broken',
        expect_error=True,
    )
    build = script.venv_path / 'build'
    assert not exists(build), "build/ dir still exists: %s" % result.stdout
    script.assert_no_temp()


def test_cleanup_after_egg_info_exception(script, data):
    """
    Test clean up after a 'setup.py egg_info' exception.
    """
    # brokenegginfo fails during egg_info; see packages readme file
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'brokenegginfo==0.1',
        expect_error=True,
    )
    build = script.venv_path / 'build'
    assert not exists(build), "build/ dir still exists: %s" % result.stdout
    script.assert_no_temp()


@pytest.mark.network
def test_cleanup_prevented_upon_build_dir_exception(script, data):
    """
    Test no cleanup occurs after a PreviousBuildDirError
    """
    build = script.venv_path / 'build'
    build_simple = build / 'simple'
    os.makedirs(build_simple)
    write_delete_marker_file(build_simple)
    build_simple.joinpath("setup.py").write_text("#")
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple',
        '--build', build,
        expect_error=True, expect_temp=True,
    )

    assert result.returncode == PREVIOUS_BUILD_DIR_ERROR, str(result)
    assert "pip can't proceed" in result.stderr, str(result)
    assert exists(build_simple), str(result)


@pytest.mark.network
def test_pep517_no_legacy_cleanup(script, data, with_wheel):
    """Test a PEP 517 failed build does not attempt a legacy cleanup"""
    to_install = data.packages.joinpath('pep517_wrapper_buildsys')
    script.environ["PIP_TEST_FAIL_BUILD_WHEEL"] = "1"
    res = script.pip(
        'install', '-f', data.find_links, to_install,
        expect_error=True
    )
    # Must not have built the package
    expected = "Failed building wheel for pep517-wrapper-buildsys"
    assert expected in str(res)
    # Must not have attempted legacy cleanup
    assert "setup.py clean" not in str(res)
