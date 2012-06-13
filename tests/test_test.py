"""Test the test support."""

import sys
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


