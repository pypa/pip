"""'pip wheel' tests"""
import os.path
import pytest

from pip.locations import write_delete_marker_file
from tests.lib import pyversion


def test_pip_wheel_fails_without_wheel(script, data):
    """
    Test 'pip wheel' fails without wheel
    """
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple==3.0',
        expect_error=True,
    )
    assert "'pip wheel' requires the 'wheel' package" in result.stderr


@pytest.mark.network
def test_pip_wheel_success(script, data):
    """
    Test 'pip wheel' success.
    """
    script.pip('install', 'wheel')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple==3.0',
    )
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / 'wheelhouse' / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" in result.stdout, result.stdout


@pytest.mark.network
def test_pip_wheel_downloads_wheels(script, data):
    """
    Test 'pip wheel' downloads wheels
    """
    script.pip('install', 'wheel')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'simple.dist',
    )
    wheel_file_name = 'simple.dist-0.1-py2.py3-none-any.whl'
    wheel_file_path = script.scratch / 'wheelhouse' / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Saved" in result.stdout, result.stdout


@pytest.mark.network
def test_pip_wheel_builds_when_no_binary_set(script, data):
    script.pip('install', 'wheel')
    res = script.pip(
        'wheel', '--no-index', '--no-binary', ':all:', '-f', data.find_links,
        'setuptools==0.9.8')
    assert "Running setup.py bdist_wheel for setuptools" in str(res), str(res)


@pytest.mark.network
def test_pip_wheel_builds_editable_deps(script, data):
    """
    Test 'pip wheel' finds and builds dependencies of editables
    """
    script.pip('install', 'wheel')
    editable_path = os.path.join(data.src, 'requires_simple')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, '-e', editable_path
    )
    wheel_file_name = 'simple-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / 'wheelhouse' / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout


@pytest.mark.network
def test_pip_wheel_fail(script, data):
    """
    Test 'pip wheel' failure.
    """
    script.pip('install', 'wheel')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'wheelbroken==0.1',
        expect_error=True,
    )
    wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / 'wheelhouse' / wheel_file_name
    assert wheel_file_path not in result.files_created, (
        wheel_file_path,
        result.files_created,
    )
    assert "FakeError" in result.stdout, result.stdout
    assert "Failed to build wheelbroken" in result.stdout, result.stdout
    assert result.returncode != 0


@pytest.mark.network
def test_no_clean_option_blocks_cleaning_after_wheel(script, data):
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    script.pip('install', 'wheel')
    build = script.venv_path / 'build'
    result = script.pip(
        'wheel', '--no-clean', '--no-index', '--build', build,
        '--find-links=%s' % data.find_links, 'simple',
    )
    found = False
    for path, subdirs, _ in os.walk(build):
        if 'simple' in subdirs:
            return
    assert 0, 'simple build dir not found'


@pytest.mark.network
def test_pip_wheel_source_deps(script, data):
    """
    Test 'pip wheel' finds and builds source archive dependencies
    of wheels
    """
    # 'requires_source' is a wheel that depends on the 'source' project
    script.pip('install', 'wheel')
    result = script.pip(
        'wheel', '--no-index', '-f', data.find_links, 'requires_source',
    )
    wheel_file_name = 'source-1.0-py%s-none-any.whl' % pyversion[0]
    wheel_file_path = script.scratch / 'wheelhouse' / wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built source" in result.stdout, result.stdout
