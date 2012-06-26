import pip.download
from pip.commands.search import (compare_versions,
                                 highest_version,
                                 transform_hits,
                                 SearchCommand)
from pip.status_codes import NO_MATCHES_FOUND, SUCCESS
from pip.backwardcompat import xmlrpclib, b
from mock import Mock
from tests.test_pip import run_pip, reset_env, pyversion
from tests.pypi_server import assert_equal


if pyversion >= '3':
    VERBOSE_FALSE = False
else:
    VERBOSE_FALSE = 0


def test_version_compare():
    """
    Test version comparison.

    """
    assert compare_versions('1.0', '1.1') == -1
    assert compare_versions('1.1', '1.0') == 1
    assert compare_versions('1.1a1', '1.1') == -1
    assert compare_versions('1.1.1', '1.1a') == -1
    assert highest_version(['1.0', '2.0', '0.1']) == '2.0'
    assert highest_version(['1.0a1', '1.0']) == '1.0'


def test_pypi_xml_transformation():
    """
    Test transformation of data structures (pypi xmlrpc to custom list).

    """
    pypi_hits = [{'_pypi_ordering': 100, 'name': 'foo', 'summary': 'foo summary', 'version': '1.0'},
            {'_pypi_ordering': 200, 'name': 'foo', 'summary': 'foo summary v2', 'version': '2.0'},
            {'_pypi_ordering': 50, 'name': 'bar', 'summary': 'bar summary', 'version': '1.0'}]
    expected = [{'score': 200, 'versions': ['1.0', '2.0'], 'name': 'foo', 'summary': 'foo summary v2'},
            {'score': 50, 'versions': ['1.0'], 'name': 'bar', 'summary': 'bar summary'}]
    assert_equal(transform_hits(pypi_hits), expected)


def test_invalid_pypi_transformation():
    """
    Test transformation of pypi when ordering None
    """
    pypi_hits = [{'_pypi_ordering': None, 'name': 'bar', 'summary': 'bar summary', 'version': '1.0'},
        {'_pypi_ordering': 100, 'name': 'foo', 'summary': 'foo summary', 'version': '1.0'}]

    expected = [{'score': 100, 'versions': ['1.0'], 'name': 'foo', 'summary': 'foo summary'},
            {'score': 0, 'versions': ['1.0'], 'name': 'bar', 'summary': 'bar summary'}]
    assert_equal(transform_hits(pypi_hits), expected)


def test_search():
    """
    End to end test of search command.

    """
    reset_env()
    output = run_pip('search', 'pip')
    assert 'pip installs packages' in output.stdout


def test_multiple_search():
    """
    Test searching for multiple packages at once.

    """
    reset_env()
    output = run_pip('search', 'pip', 'INITools')
    assert 'pip installs packages' in output.stdout
    assert 'Tools for parsing and using INI-style files' in output.stdout


def test_searching_through_Search_class():
    """
    Verify if ``pip.vcs.Search`` uses tests xmlrpclib.Transport class
    """
    original_xmlrpclib_transport = pip.download.xmlrpclib_transport
    pip.download.xmlrpclib_transport = fake_transport = Mock()
    query = 'mylittlequerythatdoesnotexists'
    dumped_xmlrpc_request = b(xmlrpclib.dumps(({'name': query, 'summary': query}, 'or'), 'search'))
    expected = [{'_pypi_ordering': 100, 'name': 'foo', 'summary': 'foo summary', 'version': '1.0'}]
    fake_transport.request.return_value = (expected,)
    pypi_searcher = SearchCommand()
    result = pypi_searcher.search(query, 'http://pypi.python.org/pypi')
    try:
        assert expected == result, result
        fake_transport.request.assert_called_with('pypi.python.org', '/pypi', dumped_xmlrpc_request, verbose=VERBOSE_FALSE)
    finally:
        pip.download.xmlrpclib_transport = original_xmlrpclib_transport


def test_search_missing_argument():
    """
    Test missing required argument for search
    """
    env = reset_env(use_distribute=True)
    result = run_pip('search', expect_error=True)
    assert 'ERROR: Missing required argument (search query).' in result.stdout


def test_run_method_should_return_sucess_when_find_packages():
    """
    Test SearchCommand.run for found package
    """
    options_mock = Mock()
    options_mock.index = 'http://pypi.python.org/pypi'
    search_cmd = SearchCommand()
    status = search_cmd.run(options_mock, ('pip',))
    assert status == SUCCESS


def test_run_method_should_return_no_matches_found_when_does_not_find_packages():
    """
    Test SearchCommand.run for no matches
    """
    options_mock = Mock()
    options_mock.index = 'http://pypi.python.org/pypi'
    search_cmd = SearchCommand()
    status = search_cmd.run(options_mock, ('non-existant-package',))
    assert status == NO_MATCHES_FOUND, status


def test_search_should_exit_status_code_zero_when_find_packages():
    """
    Test search exit status code for package found
    """
    env = reset_env(use_distribute=True)
    result = run_pip('search', 'pip')
    assert result.returncode == SUCCESS


def test_search_exit_status_code_when_finds_no_package():
    """
    Test search exit status code for no matches
    """
    env = reset_env(use_distribute=True)
    result = run_pip('search', 'non-existant-package', expect_error=True)
    assert result.returncode == NO_MATCHES_FOUND
