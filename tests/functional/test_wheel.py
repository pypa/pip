"""'pip wheel' tests"""
import os
import re
from os.path import exists

import pytest

from pip._internal.cli.status_codes import ERROR, PREVIOUS_BUILD_DIR_ERROR
from pip._internal.utils.marker_files import write_delete_marker_file
from tests.lib import pyversion


@pytest.fixture(autouse=True)
def auto_with_wheel(with_wheel):
    pass


def add_files_to_dist_directory(folder):
    (folder / 'dist').mkdir(parents=True)
    (folder / 'dist' / 'a_name-0.0.1.tar.gz').write_text("hello")
    # Not adding a wheel file since that confuses setuptools' backend.
    # (folder / 'dist' / 'a_name-0.0.1-py2.py3-none-any.whl').write_text(
    #     "hello"
    # )


def test_wheel_exit_status_code_when_no_requirements(script):
    """
    Test wheel exit status code when no requirements specified
    """
    result = script.pip('wheel', expect_error=True)
    assert "You must give at least one requirement to wheel" in result.stderr
    assert result.returncode == ERROR


def test_wheel_exit_status_code_when_blank_requirements_file(script):
    """
    Test wheel exit status code when blank requirements file specified
    """
    script.scratch_path.joinpath("blank.txt").write_text("\n")
    script.pip('wheel', '-r', 'blank.txt')


def test_pip_wheel_success(script, data):
    """
    Test 'pip wheel' success.
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        'simple==3.0',
    )
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert re.search(
        r"Created wheel for simple: "
        r"filename=%s size=\d+ sha256=[A-Fa-f0-9]{64}"
        % re.escape(wheel_file_name), result.stdout)
    assert re.search(
        r"^\s+Stored in directory: ", result.stdout, re.M)
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" in result.stdout, result.stdout


def test_pip_wheel_build_cache(script, data):
    """
    Test 'pip wheel' builds and caches.
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        'simple==3.0',
    )
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" in result.stdout, result.stdout
    # remove target file
    (script.scratch_path / wheel_file_name).unlink()
    # pip wheel again and test that no build occurs since
    # we get the wheel from cache
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        'simple==3.0',
    )
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" not in result.stdout, result.stdout


def test_basic_pip_wheel_downloads_wheels(script, data):
    """
    Test 'pip wheel' downloads wheels
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple.dist',
    )
    wheel_file_name = 'simple.dist-0.1-py2.py3-none-any.whl'
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Saved" in result.stdout, result.stdout


def test_pip_wheel_build_relative_cachedir(script, data):
    """
    Test 'pip wheel' builds and caches with a non-absolute cache directory.
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        '--cache-dir', './cache',
        'simple==3.0',
    )
    assert result.returncode == 0


def test_pip_wheel_builds_when_no_binary_set(script, data):
    data.packages.joinpath('simple-3.0-py2.py3-none-any.whl').touch()
    # Check that the wheel package is ignored
    res = script.pip(
        'wheel', '--no-index', '--no-binary', ':all:',
        '-f', data.find_links,
        'simple==3.0')
    assert "Building wheel for simple" in str(res), str(res)


@pytest.mark.skipif("sys.platform == 'win32'")
def test_pip_wheel_readonly_cache(script, data, tmpdir):
    cache_dir = tmpdir / "cache"
    cache_dir.mkdir()
    os.chmod(cache_dir, 0o400)  # read-only cache
    # Check that the wheel package is ignored
    res = script.pip(
        'wheel', '--no-index',
        '-f', data.find_links,
        '--cache-dir', cache_dir,
        'simple==3.0',
        allow_stderr_warning=True,
    )
    assert res.returncode == 0
    assert "The cache has been disabled." in str(res), str(res)


def test_pip_wheel_builds_editable_deps(script, data):
    """
    Test 'pip wheel' finds and builds dependencies of editables
    """
    editable_path = os.path.join(data.src, 'requires_simple')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        '-e', editable_path
    )
    wheel_file_name = 'simple-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


def test_pip_wheel_builds_editable(script, data):
    """
    Test 'pip wheel' builds an editable package
    """
    editable_path = os.path.join(data.src, 'simplewheel-1.0')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        '-e', editable_path
    )
    wheel_file_name = 'simplewheel-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


def test_pip_wheel_fail(script, data):
    """
    Test 'pip wheel' failure.
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        'wheelbroken==0.1',
        expect_error=True,
    )
    wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path not in result.files_created, (
        wheel_file_path,
        result.files_created,
    )
    assert "FakeError" in result.stderr, result.stderr
    assert "Failed to build wheelbroken" in result.stdout, result.stdout
    assert result.returncode != 0


def test_no_clean_option_blocks_cleaning_after_wheel(script, data):
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    build = script.venv_path / 'build'
    result = script.pip(
        'wheel', '--no-clean', '--no-index', '--build', build,
        '--find-links=%s' % data.find_links,
        'simple',
        expect_temp=True,
    )
    build = build / 'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


def test_pip_wheel_source_deps(script, data):
    """
    Test 'pip wheel' finds and builds source archive dependencies
    of wheels
    """
    # 'requires_source' is a wheel that depends on the 'source' project
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        'requires_source',
    )
    wheel_file_name = 'source-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built source" in result.stdout, result.stdout


def test_pip_wheel_fail_cause_of_previous_build_dir(script, data):
    """
    Test when 'pip wheel' tries to install a package that has a previous build
    directory
    """

    # Given that I have a previous build dir of the `simple` package
    build = script.venv_path / 'build' / 'simple'
    os.makedirs(build)
    write_delete_marker_file(script.venv_path / 'build' / 'simple')
    build.joinpath('setup.py').write_text('#')

    # When I call pip trying to install things again
    result = script.pip(
        'wheel', '--no-index', '--find-links=%s' % data.find_links,
        '--build', script.venv_path / 'build',
        'simple==3.0', expect_error=True, expect_temp=True,
    )

    # Then I see that the error code is the right one
    assert result.returncode == PREVIOUS_BUILD_DIR_ERROR, result


def test_wheel_package_with_latin1_setup(script, data):
    """Create a wheel from a package with latin-1 encoded setup.py."""

    pkg_to_wheel = data.packages.joinpath("SetupPyLatin1")
    result = script.pip('wheel', pkg_to_wheel)
    assert 'Successfully built SetupPyUTF8' in result.stdout


def test_pip_wheel_with_pep518_build_reqs(script, data, common_wheels):
    result = script.pip('wheel', '--no-index', '-f', data.find_links,
                        '-f', common_wheels, 'pep518==3.0',)
    wheel_file_name = 'pep518-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built pep518" in result.stdout, result.stdout
    assert "Installing build dependencies" in result.stdout, result.stdout


def test_pip_wheel_with_pep518_build_reqs_no_isolation(script, data):
    script.pip_install_local('simplewheel==2.0')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links,
        '--no-build-isolation', 'pep518==3.0',
    )
    wheel_file_name = 'pep518-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built pep518" in result.stdout, result.stdout
    assert "Installing build dependencies" not in result.stdout, result.stdout


def test_pip_wheel_with_user_set_in_config(script, data, common_wheels):
    config_file = script.scratch_path / 'pip.conf'
    script.environ['PIP_CONFIG_FILE'] = str(config_file)
    config_file.write_text("[install]\nuser = true")
    result = script.pip(
        'wheel', data.src / 'withpyproject',
        '--no-index', '-f', common_wheels
    )
    assert "Successfully built withpyproject" in result.stdout, result.stdout


@pytest.mark.network
def test_pep517_wheels_are_not_confused_with_other_files(script, tmpdir, data):
    """Check correct wheels are copied. (#6196)
    """
    pkg_to_wheel = data.src / 'withpyproject'
    add_files_to_dist_directory(pkg_to_wheel)

    result = script.pip('wheel', pkg_to_wheel, '-w', script.scratch_path)
    assert "Installing build dependencies" in result.stdout, result.stdout

    wheel_file_name = 'withpyproject-0.0.1-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


def test_legacy_wheels_are_not_confused_with_other_files(script, tmpdir, data):
    """Check correct wheels are copied. (#6196)
    """
    pkg_to_wheel = data.src / 'simplewheel-1.0'
    add_files_to_dist_directory(pkg_to_wheel)

    result = script.pip('wheel', pkg_to_wheel, '-w', script.scratch_path)
    assert "Installing build dependencies" not in result.stdout, result.stdout

    wheel_file_name = 'simplewheel-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
