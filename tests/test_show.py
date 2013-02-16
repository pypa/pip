from __future__ import with_statement

import re
import contextlib
import pip.download
from mock import patch, Mock
from pip import __version__
from pip.commands.show import search_packages_info, ShowCommand
from pip.baseparser import create_main_parser
from tests.test_pip import reset_env, run_pip
from pip.status_codes import NO_MATCHES_FOUND, SUCCESS


def test_show():
    """
    Test end to end test for show command.

    """
    reset_env()
    result = run_pip('show', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 6
    assert lines[0] == '---', lines[0]
    assert lines[1] == 'Name: pip', lines[1]
    assert lines[2] == 'Version: %s' % __version__, lines[2]
    assert lines[3].startswith('Location: '), lines[3]
    assert lines[4] == 'Requires: '


def test_show_with_files_not_found():
    """
    Test for show command with installed files listing enabled and
    installed-files.txt not found.

    """
    reset_env()
    result = run_pip('show', '-f', 'pip')
    lines = result.stdout.split('\n')
    assert len(lines) == 8
    assert lines[0] == '---', lines[0]
    assert lines[1] == 'Name: pip', lines[1]
    assert lines[2] == 'Version: %s' % __version__, lines[2]
    assert lines[3].startswith('Location: '), lines[3]
    assert lines[4] == 'Requires: '
    assert lines[5] == 'Files:', lines[4]
    assert lines[6] == 'Cannot locate installed-files.txt', lines[5]


def test_show_with_all_files():
    """
    Test listing all files in the show command.

    """
    reset_env()
    result = run_pip('install', 'initools==0.2')
    result = run_pip('show', '--files', 'initools')
    assert re.search(r"Files:\n(  .+\n)+", result.stdout)


def test_missing_argument():
    """
    Test show command with no arguments.

    """
    reset_env()
    result = run_pip('show')
    assert 'ERROR: Please provide one or more package names.' in result.stdout


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


initools_release_data = {
    '_pypi_hidden': False,
    '_pypi_ordering': 13,
    'author': 'Ian Bicking',
    'author_email': 'ianb@colorstudy.com',
    'bugtrack_url': None,
    'cheesecake_code_kwalitee_id': None,
    'cheesecake_documentation_id': None,
    'cheesecake_installability_id': None,
    'classifiers': ['Intended Audience :: Developers',
                    'License :: OSI Approved :: MIT License',
                    'Topic :: Software Development :: Libraries'],
    'description': '''\
A set of tools for parsing and using ``.ini``-style files, including
an abstract parser and several tools built on that parser.

Repository available at `http://bitbucket.org/ianb/initools
<http://bitbucket.org/ianb/initools>`_, or `download a tarball
of the development version
<http://bitbucket.org/ianb/initools/get/tip.gz#egg=INITools-dev>`_
using ``easy_install INITools==dev``''',
    'docs_url': '',
    'download_url': 'UNKNOWN',
    'home_page': 'http://pythonpaste.org/initools/',
    'keywords': 'config parser ini',
    'license': 'MIT',
    'maintainer': None,
    'maintainer_email': None,
    'name': 'INITools',
    'package_url': 'http://pypi.python.org/pypi/INITools',
    'platform': 'UNKNOWN',
    'release_url': 'http://pypi.python.org/pypi/INITools/0.3.1',
    'requires_python': None,
    'stable_version': None,
    'summary': 'Tools for parsing and using INI-style files',
    'version': '0.3.1'}


initools_search = [
    {'_pypi_ordering': 9999,
     'name': 'INITools',
     'summary': 'Tools for parsing and using INI-style files',
     'version': '0.3.1'}]


def transport_side_effects(*args, **kwargs):
    name = initools_search[0]['name'].encode('utf-8')
    if 'search'.encode('utf-8') in args[2]:
        if re.search(name, args[2], re.I):
            return (initools_search,)
        else:
            return []
    if 'release_data'.encode('utf-8') in args[2]:
        if re.search(name, args[2], re.I):
            return (initools_release_data,)


def test_pypi_show():
    "Test getting package information from PyPi."
    options = Mock()
    options.use_pypi = True
    options.index_url = 'http://pypi.python.org/pypi'

    @contextlib.contextmanager
    def command():
        with patch('pip.download.xmlrpclib_transport') as transport:
            cmd = ShowCommand(create_main_parser())
            transport.request.side_effect = transport_side_effects
            yield cmd, transport.request

    with command() as (cmd, request):
        res = cmd.run(options, ['INITools'])
        assert res == SUCCESS
        assert request.call_count == 2

    with command() as (cmd, request):
        res = cmd.run(options, ['#$@#ASDOASD'])
        assert res == NO_MATCHES_FOUND

    with command() as (cmd, request):
        res = cmd.run(options, ['initools', '#$@#ASDOASD', 'INITools'])
        assert request.call_count == 3  # 2 search() + 1 request_data()
        assert res == SUCCESS
