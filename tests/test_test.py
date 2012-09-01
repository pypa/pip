"""Test the test support."""

import sys
import os
from os.path import abspath, join, curdir, isdir, isfile
from nose import SkipTest
from tests.local_repos import local_checkout
from tests.test_pip import here, reset_env, run_pip, pyversion


patch_urlopen = """
       def mock_urlopen():
           pass
       import pip
       pip.backwardcompat.urllib2.urlopen = mock_urlopen
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
    assert here not in paths, paths


def test_add_patch_to_sitecustomize():
    """
    Test adding monkey patch snippet to sitecustomize.py (using TestPipEnvironment)
    """

    env = reset_env(sitecustomize=patch_urlopen, use_distribute=True)
    result = env.run('python', '-c', "import pip; print(pip.backwardcompat.urllib2.urlopen.__module__)")
    assert "sitecustomize"== result.stdout.strip(), result.stdout


def test_add_patch_to_sitecustomize_fast():
    """
    Test adding monkey patch snippet to sitecustomize.py (using FastTestPipEnvironment)
    """

    env = reset_env(sitecustomize=patch_urlopen)
    result = env.run('python', '-c', "import pip; print(pip.backwardcompat.urllib2.urlopen.__module__)")
    assert "sitecustomize"== result.stdout.strip(), result.stdout


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
    Test that $TMPDIR == env.temp_path and path exists, and env.assert_no_temp() passes
    """
    #need these tests to ensure the assert_no_temp feature of scripttest is working
    env = reset_env(use_distribute=True)
    env.assert_no_temp() #this fails if env.tmp_path doesn't exist
    assert env.environ['TMPDIR'] == env.temp_path
    assert isdir(env.temp_path)


def test_tmp_dir_exists_in_fast_env():
    """
    Test that $TMPDIR == env.temp_path and path exists and env.assert_no_temp() passes (in fast env)
    """
    #need these tests to ensure the assert_no_temp feature of scripttest is working
    env = reset_env()
    env.assert_no_temp() #this fails if env.tmp_path doesn't exist
    assert env.environ['TMPDIR'] == env.temp_path
    assert isdir(env.temp_path)
