import re
import pkg_resources
from pip import __version__
from pip.commands.status import search_packages_info
from tests.test_pip import reset_env, run_pip


def test_status():
    """
    Test end to end test for status command.

    """
    dist = pkg_resources.get_distribution('pip')
    reset_env()
    result = run_pip('status', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 7
    assert '---', lines[0]
    assert re.match('^Name\: pip$', lines[1])
    assert re.match('^Version\: %s$' % __version__, lines[2])
    assert 'Location: %s' % dist.location, lines[3]
    assert 'Files:' == lines[4]
    assert 'Cannot locate installed-files.txt' == lines[5]


def test_missing_argument():
    """
    Test status command with no arguments.

    """
    dist = pkg_resources.get_distribution('pip')
    reset_env()
    result = run_pip('status')
    assert 'ERROR: Missing required argument (status query).' in result.stdout


def test_find_package_not_found():
    """
    Test trying to get info about a inexistent package.

    """
    result = search_packages_info(['abcd3'])
    assert len(list(result)) == 0


def test_search_any_case():
    """
    Search for a package in any case.

    """
    result = list(search_packages_info(['PIP']))
    assert len(result) == 1
    assert 'pip' == result[0]['name']


def test_more_than_one_package():
    """
    Search for more than one package.

    """
    result = list(search_packages_info(['Pip', 'Nose', 'Virtualenv']))
    assert len(result) == 3
