"""Tests for wheel binary packages and .dist-info."""
import os
import sys
import textwrap

from nose import SkipTest
from pip import wheel
from tests.test_pip import here, reset_env, run_pip, pyversion_nodot, write_file, path_to_url


FIND_LINKS = path_to_url(os.path.join(here, 'packages'))

def test_uninstallation_paths():
    class dist(object):
        def get_metadata_lines(self, record):
            return ['file.py,,',
                    'file.pyc,,',
                    'file.so,,',
                    'nopyc.py']
        location = ''

    d = dist()

    paths = list(wheel.uninstallation_paths(d))

    expected = ['file.py',
                'file.pyc',
                'file.so',
                'nopyc.py',
                'nopyc.pyc']

    assert paths == expected

    # Avoid an easy 'unique generator' bug
    paths2 = list(wheel.uninstallation_paths(d))

    assert paths2 == paths


class TestPipWheel:

    def setup(self):
        if sys.version_info < (2, 6):
            raise SkipTest() #bdist_wheel fails in py25?

    def test_pip_wheel_success(self):
        """
        Test 'pip wheel' success.
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        run_pip('install', 'markerlib')
        result = run_pip('wheel', '--no-index', '-f', FIND_LINKS, 'simple==3.0')
        wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path in result.files_created, result.stdout
        assert "Successfully built simple" in result.stdout, result.stdout


    def test_pip_wheel_fail(self):
        """
        Test 'pip wheel' failure.
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        run_pip('install', 'markerlib')
        result = run_pip('wheel', '--no-index', '-f', FIND_LINKS, 'wheelbroken==0.1')
        wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path not in result.files_created, (wheel_file_path, result.files_created)
        assert "FakeError" in result.stdout, result.stdout
        assert "Failed to build wheelbroken" in result.stdout, result.stdout


    def test_pip_wheel_ignore_wheels_editables(self):
        """
        Test 'pip wheel' ignores editables and *.whl files in requirements
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        run_pip('install', 'markerlib')

        local_wheel = '%s/simple.dist-0.1-py2.py3-none-any.whl' % FIND_LINKS
        local_editable = os.path.abspath(os.path.join(here, 'packages', 'FSPkg'))
        write_file('reqs.txt', textwrap.dedent("""\
            %s
            -e %s
            simple
            """ % (local_wheel, local_editable)))
        result = run_pip('wheel', '--no-index', '-f', FIND_LINKS, '-r', env.scratch_path / 'reqs.txt')
        wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path in result.files_created, (wheel_file_path, result.files_created)
        assert "Successfully built simple" in result.stdout, result.stdout
        assert "Failed to build" not in result.stdout, result.stdout
        assert "ignoring %s" % local_wheel in result.stdout
        assert "ignoring file://%s" % local_editable in result.stdout, result.stdout


    def test_pip_wheel_unpack_only(self):
        """
        Test 'pip wheel' unpack only.
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        run_pip('install', 'markerlib')
        result = run_pip('wheel', '--unpack-only', '--no-index', '-f', FIND_LINKS, 'simple==3.0')
        wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path not in result.files_created, (wheel_file_path, result.files_created)
        assert env.venv/'build'/'simple'/'setup.py' in result.files_created, result.files_created

