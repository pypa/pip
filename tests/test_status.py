import re
from pip import __version__
from pip.commands.status import search_packages_info
from tests.test_pip import reset_env, run_pip


def test_status():
    """
    Test end to end test for status command.

    """
    reset_env()
    result = run_pip('status', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 5
    assert lines[0] == '---', lines[0]
    assert lines[1] == 'Name: pip', lines[1]
    assert lines[2] == 'Version: %s' % __version__, lines[2]
    assert lines[3].startswith('Location: '), lines[3]


def test_status_with_files_not_found():
    """
    Test for status command with installed files listing enabled and 
    installed-files.txt not found.

    """
    reset_env()
    result = run_pip('status', '-f', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 7
    assert lines[0] == '---', lines[0]
    assert lines[1] == 'Name: pip', lines[1]
    assert lines[2] == 'Version: %s' % __version__, lines[2]
    assert lines[3].startswith('Location: '), lines[3]
    assert lines[4] ==  'Files:', lines[4]
    assert lines[5] == 'Cannot locate installed-files.txt', lines[5]


def test_status_with_all_files():
    """
    Test listing all files in the status command.

    """
    reset_env()
    result = run_pip('install', 'initools==0.2')
    result = run_pip('status', '--files', 'initools')
    assert re.search(r"Files:\n(  .+\n)+", result.stdout)


def test_missing_argument():
    """
    Test status command with no arguments.

    """
    reset_env()
    result = run_pip('status')
    assert 'ERROR: Please provide a project name or names.' in result.stdout


def test_find_package_not_found():
    """
    Test trying to get info about a nonexistent package.

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
