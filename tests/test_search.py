import xmlrpclib
import pip.download
from pip.commands.search import (compare_versions,
                                 highest_version,
                                 transform_hits,
                                 SearchCommand,)
from mock import Mock
from test_pip import run_pip, reset_env


def test_version_compare():
    """
    Test version comparison.

    """
    assert compare_versions('1.0', '1.1') == -1
    assert compare_versions('1.1', '1.0') == 1
    assert compare_versions('1.1a1', '1.1') == -1
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
    assert expected == transform_hits(pypi_hits)


def test_search():
    """
    End to end test of search command.

    """
    reset_env()
    output = run_pip('search', 'pip', expect_error=True)
    assert 'pip installs packages' in output.stdout


def test_searching_through_Search_class():
    """
    Verify if ``pip.vcs.Search`` uses tests xmlrpclib.Transport class
    """
    pip.download.xmlrpclib_transport = fake_transport = Mock()
    query = 'mylittlequerythatdoesnotexists'
    dumped_xmlrpc_request = xmlrpclib.dumps(({'name': query, 'summary': query}, 'or'), 'search')
    expected = [{'_pypi_ordering': 100, 'name': 'foo', 'summary': 'foo summary', 'version': '1.0'}]
    fake_transport.request.return_value = (expected,)
    pypi_searcher = SearchCommand()
    result = pypi_searcher.search(query, 'http://pypi.python.org/pypi')
    assert expected == result, result
    fake_transport.request.assert_called_with('pypi.python.org', '/pypi', dumped_xmlrpc_request, verbose=0)
