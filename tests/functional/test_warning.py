import pytest


@pytest.mark.skipif("sys.version_info < (2,7)")
def test_environ(script, tmpdir):
    """$PYTHONWARNINGS was added in python2.7"""
    demo = tmpdir.join('warnings_demo.py')
    demo.write('''
from pip.utils import deprecation
deprecation.install_warning_logger()

from logging import basicConfig
basicConfig()

from warnings import warn
warn("deprecated!", deprecation.PipDeprecationWarning)
''')

    result = script.run('python', demo, expect_stderr=True)
    assert result.stderr == 'ERROR:pip.deprecations:DEPRECATION: deprecated!\n'

    script.environ['PYTHONWARNINGS'] = 'ignore'
    result = script.run('python', demo)
    assert result.stderr == ''
