"""'pip wheel' tests"""
import os
from os.path import exists

import pytest

from pip._internal.locations import write_delete_marker_file
from pip._internal.status_codes import ERROR, PREVIOUS_BUILD_DIR_ERROR
from tests.lib import pyversion


def test_basic_pip_wheel_fails_without_wheel(script, data):
    """
    Test 'pip wheel' fails without wheel
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple==3.0',
        expect_error=True,
    )
    assert "'pip wheel' requires the 'wheel' package" in result.stderr


def test_wheel_exit_status_code_when_no_requirements(script, common_wheels):
    """
    Test wheel exit status code when no requirements specified
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    result = script.pip('wheel', expect_error=True)
    assert "You must give at least one requirement to wheel" in result.stderr
    assert result.returncode == ERROR


def test_wheel_exit_status_code_when_blank_requirements_file(
        script, common_wheels):
    """
    Test wheel exit status code when blank requirements file specified
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    script.scratch_path.join("blank.txt").write("\n")
    script.pip('wheel', '-r', 'blank.txt')


@pytest.mark.network
def test_pip_wheel_success(script, data, common_wheels):
    """
    Test 'pip wheel' success.
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-f', common_wheels,
        'simple==3.0',
    )
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" in result.stdout, result.stdout


@pytest.mark.network
def test_basic_pip_wheel_downloads_wheels(script, data, common_wheels):
    """
    Test 'pip wheel' downloads wheels
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple.dist',
    )
    wheel_file_name = 'simple.dist-0.1-py2.py3-none-any.whl'
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Saved" in result.stdout, result.stdout


@pytest.mark.network
def test_pip_wheel_builds_when_no_binary_set(script, data, common_wheels):
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    data.packages.join('simple-3.0-py2.py3-none-any.whl').touch()
    # Check that the wheel package is ignored
    res = script.pip(
        'wheel', '--no-index', '--no-binary', ':all:',
        '-f', data.find_links, '-f', common_wheels,
        'simple==3.0')
    assert "Running setup.py bdist_wheel for simple" in str(res), str(res)


@pytest.mark.network
def test_pip_wheel_builds_editable_deps(script, data, common_wheels):
    """
    Test 'pip wheel' finds and builds dependencies of editables
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    editable_path = os.path.join(data.src, 'requires_simple')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-f', common_wheels,
        '-e', editable_path
    )
    wheel_file_name = 'simple-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


@pytest.mark.network
def test_pip_wheel_builds_editable(script, data, common_wheels):
    """
    Test 'pip wheel' builds an editable package
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    editable_path = os.path.join(data.src, 'simplewheel-1.0')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-f', common_wheels,
        '-e', editable_path
    )
    wheel_file_name = 'simplewheel-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


@pytest.mark.network
def test_pip_wheel_fail(script, data, common_wheels):
    """
    Test 'pip wheel' failure.
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-f', common_wheels,
        'wheelbroken==0.1',
        expect_error=True,
    )
    wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path not in result.files_created, (
        wheel_file_path,
        result.files_created,
    )
    assert "FakeError" in result.stdout, result.stdout
    assert "Failed to build wheelbroken" in result.stdout, result.stdout
    assert result.returncode != 0


@pytest.mark.network
def test_no_clean_option_blocks_cleaning_after_wheel(
        script, data, common_wheels):
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    build = script.venv_path / 'build'
    result = script.pip(
        'wheel', '--no-clean', '--no-index', '--build', build,
        '--find-links=%s' % data.find_links, '-f', common_wheels,
        'simple',
        expect_temp=True,
    )
    build = build / 'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


@pytest.mark.network
def test_pip_wheel_source_deps(script, data, common_wheels):
    """
    Test 'pip wheel' finds and builds source archive dependencies
    of wheels
    """
    # 'requires_source' is a wheel that depends on the 'source' project
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-f', common_wheels,
        'requires_source',
    )
    wheel_file_name = 'source-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built source" in result.stdout, result.stdout


@pytest.mark.network
def test_pip_wheel_fail_cause_of_previous_build_dir(
        script, data, common_wheels):
    """
    Test when 'pip wheel' tries to install a package that has a previous build
    directory
    """

    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)

    # Given that I have a previous build dir of the `simple` package
    build = script.venv_path / 'build' / 'simple'
    os.makedirs(build)
    write_delete_marker_file(script.venv_path / 'build')
    build.join('setup.py').write('#')

    # When I call pip trying to install things again
    result = script.pip(
        'wheel', '--no-index', '--find-links=%s' % data.find_links,
        '--build', script.venv_path / 'build',
        'simple==3.0', expect_error=True, expect_temp=True,
    )

    # Then I see that the error code is the right one
    assert result.returncode == PREVIOUS_BUILD_DIR_ERROR, result


@pytest.mark.network
def test_wheel_package_with_latin1_setup(script, data, common_wheels):
    """Create a wheel from a package with latin-1 encoded setup.py."""
    script.pip('install', 'wheel', '--no-index', '-f', common_wheels)

    pkg_to_wheel = data.packages.join("SetupPyLatin1")
    result = script.pip('wheel', pkg_to_wheel)
    assert 'Successfully built SetupPyUTF8' in result.stdout


@pytest.mark.network
def test_pip_wheel_with_pep518_build_reqs(script, data):
    script.pip('install', 'wheel')
    script.pip('download', 'setuptools', 'wheel', '-d', data.packages)
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'pep518==3.0',
    )
    wheel_file_name = 'pep518-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built pep518" in result.stdout, result.stdout
    assert "Installing build dependencies" in result.stdout, result.stdout
