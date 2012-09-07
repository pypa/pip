import re
import pkg_resources
from pip import __version__
from tests.test_pip import reset_env, run_pip

def test_status():
    """
    Test end to end test for status command.

    """
    dist = pkg_resources.get_distribution('pip')
    reset_env()
    result = run_pip('status', 'pip')
    lines = result.stdout.split('\n')
    assert 7 == len(lines)
    assert '---', lines[0]
    assert re.match('^Name\: pip$', lines[1])
    assert re.match('^Version\: %s$' % __version__, lines[2])
    assert 'Location: %s' % dist.location, lines[3]
    assert 'Files:' == lines[4]
    assert 'Cannot locate installed-files.txt' == lines[5]
