import os

from os.path import exists

from tests.lib.local_repos import local_checkout
from tests.lib.path import Path
from pip.locations import write_delete_marker_file
from pip.status_codes import PREVIOUS_BUILD_DIR_ERROR


def test_cleanup_after_install(script, data):
    """
    Test clean up after installing a package.
    """
    script.pip(
        'install', '--no-index', '--find-links=%s' % data.find_links, 'simple'
    )
    build = script.venv_path / "build"
    src = script.venv_path / "src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert not exists(src), "unexpected src/ dir exists: %s" % src
    script.assert_no_temp()


def test_no_clean_option_blocks_cleaning_after_install(script, data):
    """
    Test --no-clean option blocks cleaning after install
    """
    result = script.pip(
        'install', '--no-clean', '--no-index',
        '--find-links=%s' % data.find_links, 'simple'
    )
    build = script.venv_path / 'build' / 'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


def test_cleanup_after_install_editable_from_hg(script, tmpdir):
    """
    Test clean up after cloning from Mercurial.

    """
    script.pip(
        'install',
        '-e',
        '%s#egg=ScriptTest' %
        local_checkout(
            'hg+https://bitbucket.org/ianb/scripttest',
            tmpdir.join("cache"),
        ),
        expect_error=True,
    )
    build = script.venv_path / 'build'
    src = script.venv_path / 'src'
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src
    script.assert_no_temp()


def test_cleanup_after_install_from_local_directory(script, data):
    """
    Test clean up after installing from a local directory.
    """
    to_install = data.packages.join("FSPkg")
    script.pip('install', to_install, expect_error=False)
    build = script.venv_path / 'build'
    src = script.venv_path / 'src'
    assert not exists(build), "unexpected build/ dir exists: %s" % build
    assert not exists(src), "unexpected src/ dir exist: %s" % src
    script.assert_no_temp()


def test_no_install_and_download_should_not_leave_build_dir(script):
    """
    It should remove build/ dir if it was pip that created
    """
    script.scratch_path.join("downloaded_packages").mkdir()
    assert not os.path.exists(script.venv_path / 'build')
    result = script.pip(
        'install', '--no-install', 'INITools==0.2', '-d', 'downloaded_packages'
    )
    assert (
        Path('scratch') / 'downloaded_packages/build'
        not in result.files_created
    ), 'pip should not leave build/ dir'
    assert not os.path.exists(script.venv_path / 'build'), (
        "build/ dir should be deleted"
    )


def test_cleanup_req_satisifed_no_name(script, data):
    """
    Test cleanup when req is already satisfied, and req has no 'name'
    """
    # this test confirms Issue #420 is fixed
    # reqs with no 'name' that were already satisfied were leaving behind tmp
    # build dirs
    # 2 examples of reqs that would do this
    # 1) https://bitbucket.org/ianb/initools/get/tip.zip
    # 2) parent-0.1.tar.gz
    dist = data.packages.join("parent-0.1.tar.gz")

    script.pip('install', dist)
    script.pip('install', dist)

    build = script.venv_path / 'build'
    assert not exists(build), "unexpected build/ dir exists: %s" % build
    script.assert_no_temp()


def test_download_should_not_delete_existing_build_dir(script):
    """
    It should not delete build/ if existing before run the command
    """
    script.venv_path.join("build").mkdir()
    script.venv_path.join("build", "somefile.txt").write("I am not empty!")
    script.pip('install', '--no-install', 'INITools==0.2', '-d', '.')
    with open(script.venv_path / 'build' / 'somefile.txt') as fp:
        content = fp.read()
    assert os.path.exists(script.venv_path / 'build'), (
        "build/ should be left if it exists before pip run"
    )
    assert content == 'I am not empty!', (
        "it should not affect build/ and its content"
    )
    assert ['somefile.txt'] == os.listdir(script.venv_path / 'build')


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


def test_cleanup_prevented_upon_build_dir_exception(script, data):
    """
    Test no cleanup occurs after a PreviousBuildDirError
    """
    build = script.venv_path / 'build' / 'simple'
    os.makedirs(build)
    write_delete_marker_file(script.venv_path / 'build')
    build.join("setup.py").write("#")
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple',
        expect_error=True,
    )

    assert result.returncode == PREVIOUS_BUILD_DIR_ERROR
    assert "pip can't proceed" in result.stdout, result.stdout
    assert exists(build)
