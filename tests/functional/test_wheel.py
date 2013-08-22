"""'pip wheel' tests"""
import os
import sys
import textwrap

from os.path import exists

from pip import wheel
from pip.download import path_to_url as path_to_url_d
from tests.lib import tests_data, reset_env, pyversion_nodot, path_to_url, find_links


def test_pip_wheel_fails_without_wheel():
    """
    Test 'pip wheel' fails without wheel
    """
    script = reset_env()
    result = script.pip('wheel', '--no-index', '-f', find_links, 'simple==3.0', expect_error=True)
    assert "'pip wheel' requires bdist_wheel" in result.stdout

def test_pip_wheel_success():
    """
    Test 'pip wheel' success.
    """
    script = reset_env()
    script.pip_install_local('wheel')
    result = script.pip('wheel', '--no-index', '-f', find_links, 'simple==3.0')
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
    wheel_file_path = script.scratch/'wheelhouse'/wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built simple" in result.stdout, result.stdout


def test_pip_wheel_fail():
    """
    Test 'pip wheel' failure.
    """
    script = reset_env()
    script.pip_install_local('wheel')
    result = script.pip('wheel', '--no-index', '-f', find_links, 'wheelbroken==0.1')
    wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion_nodot
    wheel_file_path = script.scratch/'wheelhouse'/wheel_file_name
    assert wheel_file_path not in result.files_created, (wheel_file_path, result.files_created)
    assert "FakeError" in result.stdout, result.stdout
    assert "Failed to build wheelbroken" in result.stdout, result.stdout


def test_pip_wheel_ignore_wheels_editables():
    """
    Test 'pip wheel' ignores editables and *.whl files in requirements
    """
    script = reset_env()
    script.pip_install_local('wheel')

    local_wheel = '%s/simple.dist-0.1-py2.py3-none-any.whl' % find_links
    local_editable = os.path.abspath(os.path.join(tests_data, 'packages', 'FSPkg'))
    script.scratch_path.join("reqs.txt").write(textwrap.dedent("""\
        %s
        -e %s
        simple
        """ % (local_wheel, local_editable)))
    result = script.pip('wheel', '--no-index', '-f', find_links, '-r', script.scratch_path / 'reqs.txt')
    wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
    wheel_file_path = script.scratch/'wheelhouse'/wheel_file_name
    assert wheel_file_path in result.files_created, (wheel_file_path, result.files_created)
    assert "Successfully built simple" in result.stdout, result.stdout
    assert "Failed to build" not in result.stdout, result.stdout
    assert "ignoring %s" % local_wheel in result.stdout
    ignore_editable = "ignoring %s" % path_to_url(local_editable)
    #TODO: understand this divergence
    if sys.platform == 'win32':
        ignore_editable = "ignoring %s" % path_to_url_d(local_editable)
    assert ignore_editable in result.stdout, result.stdout


def test_no_clean_option_blocks_cleaning_after_wheel():
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    script = reset_env()
    script.pip_install_local('wheel')
    result = script.pip('wheel', '--no-clean', '--no-index', '--find-links=%s' % find_links, 'simple')
    build = script.venv_path/'build'/'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


def test_pip_wheel_source_deps():
    """
    Test 'pip wheel --use-wheel' finds and builds source archive dependencies of wheels
    """
    # 'requires_source' is a wheel that depends on the 'source' project
    script = reset_env()
    script.pip_install_local('wheel')
    result = script.pip('wheel', '--use-wheel', '--no-index', '-f', find_links, 'requires_source')
    wheel_file_name = 'source-1.0-py%s-none-any.whl' % pyversion_nodot
    wheel_file_path = script.scratch/'wheelhouse'/wheel_file_name
    assert wheel_file_path in result.files_created, result.stdout
    assert "Successfully built source" in result.stdout, result.stdout
