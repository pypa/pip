import os
import tempfile
import textwrap
from tests.path import Path
from tests.test_pip import reset_env, run_pip, clear_environ, write_file, get_env


PYPIRC = r"""
[distutils]
index-servers =
    pypi

[pypi]
username:username
password:valid
repository=http://pypi.python.org/pypi/
"""

PIPCONF = r"""
[global]
timeout = 60
default-timeout = 60
respect-virtualenv = true

[install]
use-mirrors = false
"""

def test_valid_auth():
    """
    It should use .pypirc credentials to access password protected repository
    """
    here = Path(__file__).abspath.folder
    patch = r"""
            import sys
            sys.path.insert(0, %r)
            import pypi_server
            pypi_server.PyPIBasicAuthProxy.setup('username', 'valid')
            sys.path.remove(%r)""" % (str(here), str(here))

    # PyPIProxy.setup()
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    write_file(config_file, textwrap.dedent(PIPCONF))

    fd, pypirc_file = tempfile.mkstemp('-pypirc.cfg', 'test-')
    write_file(pypirc_file, textwrap.dedent(PYPIRC))

    environ = clear_environ(os.environ.copy())
    environ['PIP_CONFIG_FILE'] = config_file
    environ['PIP_PYPIRC'] = pypirc_file
    reset_env(environ, sitecustomize=patch)

    env = get_env()
    env.verbose = True
    result = run_pip('install', 'INITools==0.1', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created


def test_invalid_auth():
    """
    Should fail to access to a password protected repository
    """
    here = Path(__file__).abspath.folder
    patch = r"""
            import sys
            sys.path.insert(0, %r)
            import pypi_server
            pypi_server.PyPIBasicAuthProxy.setup('username', 'no_access_valid')
            sys.path.remove(%r)""" % (str(here), str(here))

    # PyPIProxy.setup()
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    write_file(config_file, textwrap.dedent(PIPCONF))

    fd, pypirc_file = tempfile.mkstemp('-pypirc.cfg', 'test-')
    write_file(pypirc_file, textwrap.dedent(PYPIRC))

    environ = clear_environ(os.environ.copy())
    environ['PIP_CONFIG_FILE'] = config_file
    environ['PIP_PYPIRC'] = pypirc_file
    reset_env(environ, sitecustomize=patch)

    env = get_env()
    env.verbose = True
    result = run_pip('install', 'INITools==0.1', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' not in result.files_created
    assert 'Protected repository `pypi.python.org`: unable to login' in result.stdout
    assert 'No distributions at all found for INITools==0.1' in result.stdout


def test_unparsable_pypirc():
    """
    Should fail to access because pypirc is nreadable
    """
    here = Path(__file__).abspath.folder
    patch = r"""
            import sys
            sys.path.insert(0, %r)
            import pypi_server
            pypi_server.PyPIBasicAuthProxy.setup('username', 'no_access_valid')
            sys.path.remove(%r)""" % (str(here), str(here))

    # PyPIProxy.setup()
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    write_file(config_file, textwrap.dedent(PIPCONF))

    fd, pypirc_file = tempfile.mkstemp('-pypirc.cfg', 'test-')
    write_file(pypirc_file, textwrap.dedent("""
    [distutils]
    error
    """))

    environ = clear_environ(os.environ.copy())
    environ['PIP_CONFIG_FILE'] = config_file
    environ['PIP_PYPIRC'] = pypirc_file
    reset_env(environ, sitecustomize=patch)

    env = get_env()
    env.verbose = True
    result = run_pip('install', 'INITools==0.1', '-d', '.',expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' not in result.files_created
    assert 'Unable to parse .pypirc file' in result.stdout
    assert 'No distributions at all found for INITools==0.1' in result.stdout
