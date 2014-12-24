import re
from pip import __version__
from pip.commands.show import search_packages_info


def test_show(script):
    """
    Test end to end test for show command.
    """
    result = script.pip('show', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 17
    assert lines[0] == '---', lines[0]
    assert 'Name: pip' in lines
    assert 'Version: %s' % __version__ in lines
    assert any(line.startswith('Location: ') for line in lines)
    assert 'Requires: ' in lines


def test_show_with_files_not_found(script, data):
    """
    Test for show command with installed files listing enabled and
    installed-files.txt not found.
    """
    editable = data.packages.join('SetupPyUTF8')
    script.pip('install', '-e', editable)
    result = script.pip('show', '-f', 'SetupPyUTF8')
    lines = result.stdout.split('\n')
    assert len(lines) == 14
    assert lines[0] == '---', lines[0]
    assert 'Name: SetupPyUTF8' in lines
    assert 'Version: 0.0.0' in lines
    assert any(line.startswith('Location: ') for line in lines)
    assert 'Requires: ' in lines
    assert 'Files:' in lines
    assert 'Cannot locate installed-files.txt' in lines


def test_show_with_files_from_wheel(script, data):
    """
    Test that a wheel's files can be listed
    """
    wheel_file = data.packages.join('simple.dist-0.1-py2.py3-none-any.whl')
    script.pip('install', '--no-index', wheel_file)
    result = script.pip('show', '-f', 'simple.dist')
    lines = result.stdout.split('\n')
    assert 'Name: simple.dist' in lines
    assert 'Cannot locate installed-files.txt' not in lines[6], lines[6]
    assert re.search(r"Files:\n(  .+\n)+", result.stdout)


def test_show_with_all_files(script):
    """
    Test listing all files in the show command.
    """
    script.pip('install', 'initools==0.2')
    result = script.pip('show', '--files', 'initools')
    lines = result.stdout.split('\n')
    assert 'Cannot locate installed-files.txt' not in lines[6], lines[6]
    assert re.search(r"Files:\n(  .+\n)+", result.stdout)


def test_missing_argument(script):
    """
    Test show command with no arguments.
    """
    result = script.pip('show', expect_error=True)
    assert 'ERROR: Please provide a package name or names.' in result.stdout


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
    result = list(search_packages_info(['Pip', 'pytest', 'Virtualenv']))
    assert len(result) == 3
