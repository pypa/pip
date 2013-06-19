"""Test the test support."""
import filecmp
import imp
import os
import re
import sys
from os.path import join, isdir

from nose import SkipTest
from pip.backwardcompat import uses_pycache
from tests.lib import tests_lib, reset_env, run_pip, src_folder


patch_urlopen = """
       def mock_isdir(d):
           pass
       import os
       os.path.isdir = mock_isdir
    """

def test_pypiproxy_patch_applied():
    """
    Test the PyPIProxy.setup() patch was applied, and sys.path returned to normal
    """

    env = reset_env()
    result = env.run('python', '-c', "import pip; print(pip.backwardcompat.urllib2.urlopen.__module__)")
    #if it were not patched, the result would be 'urllib2'
    assert "pypi_server"== result.stdout.strip(), result.stdout

    #confirm the temporary sys.path adjustment is gone
    result = env.run('python', '-c', "import sys; print(sys.path)")
    paths = eval(result.stdout.strip())
    assert tests_lib not in paths, paths


class Test_reset_env:

    def setup(self):

        # create a TestPipEnvironment env and add a file to the backup
        self.env = reset_env()
        self.test_file = self.env.backup_path / self.env.venv / 'test_file'
        f = open(self.test_file, 'w')
        f.close()

    def teardown(self):
        if os.path.isfile(self.test_file):
            self.test_file.rm()

    def test_cache_venv(self):
        """
        Test reset_env cache's internal virtualenv
        """
        env = reset_env()
        assert os.path.isfile(self.test_file)


    def test_reset_env_system_site_packages(self):
        """
        Test using system_site_packages with reset_env resets the venv cache
        """
        env = reset_env(system_site_packages=True)
        env = reset_env()
        assert not os.path.isfile(self.env.backup_path / self.env.venv / 'test_file')


def test_add_patch_to_sitecustomize():
    """
    Test adding monkey patch snippet to sitecustomize.py (using TestPipEnvironment)
    """

    env = reset_env(sitecustomize=patch_urlopen)

    if uses_pycache:
        # caught py32 with an outdated __pycache__ file after a sitecustomize update (after python should have updated it)
        # https://github.com/pypa/pip/pull/893#issuecomment-16426701
        # now we delete the cache file to be sure in TestPipEnvironment._add_to_sitecustomize
        # it should not exist after creating the env
        cache_path = imp.cache_from_source(env.lib_path / 'sitecustomize.py')
        assert not os.path.isfile(cache_path)

    debug_content = open(env.lib_path / 'sitecustomize.py').read()
    result = env.run('python', '-c', "import os; print(os.path.isdir.__module__)")
    if uses_pycache:
        # if this next assert fails, let's have the modified time to look at
        cache_path = imp.cache_from_source(env.lib_path / 'sitecustomize.py')
        src_mtime = os.stat(env.lib_path / 'sitecustomize.py').st_mtime
        cache_mtime = os.stat(cache_path).st_mtime
        debug_content += "src mtime: %s, cache mtime: %s" % (src_mtime, cache_mtime)
    assert "sitecustomize" == result.stdout.strip(), result.stdout


def test_sitecustomize_not_growing_in_fast_environment():
    """
    Test that the sitecustomize is not growing with redundant patches in the cached fast environment
    """

    patch = "fu = 'bar'"

    env1 = reset_env(sitecustomize=patch)
    sc1 = env1.lib_path / 'sitecustomize.py'
    size1 = os.stat(sc1).st_size
    env2 = reset_env(sitecustomize=patch)
    sc2 = env2.lib_path / 'sitecustomize.py'
    size2 = os.stat(sc2).st_size
    assert size1==size2, "size before, %d != size after, %d" %(size1, size2)


def test_tmp_dir_exists_in_env():
    """
    Test that $TMPDIR == env.temp_path and path exists and env.assert_no_temp() passes (in fast env)
    """
    #need these tests to ensure the assert_no_temp feature of scripttest is working
    env = reset_env()
    env.assert_no_temp() #this fails if env.tmp_path doesn't exist
    assert env.environ['TMPDIR'] == env.temp_path
    assert isdir(env.temp_path)


def test_correct_pip_version():
    """
    Check we are running proper version of pip in run_pip.
    """
    reset_env()

    # output is like:
    # pip PIPVERSION from PIPDIRECTORY (python PYVERSION)
    result = run_pip('--version')

    # compare the directory tree of the invoked pip with that of this source distribution
    dir = re.match(r'pip \d(\.[\d])+(\.?(rc|dev|pre|post)\d+)? from (.*) \(python \d(.[\d])+\)$',
                   result.stdout).group(4)
    pip_folder = join(src_folder, 'pip')
    pip_folder_outputed = join(dir, 'pip')

    diffs = filecmp.dircmp(pip_folder, pip_folder_outputed)

    # If any non-matching .py files exist, we have a problem: run_pip
    # is picking up some other version!  N.B. if this project acquires
    # primary resources other than .py files, this code will need
    # maintenance
    mismatch_py = [x for x in diffs.left_only + diffs.right_only + diffs.diff_files if x.endswith('.py')]
    assert not mismatch_py, 'mismatched source files in %r and %r: %r'% (pip_folder, pip_folder_outputed, mismatch_py)

