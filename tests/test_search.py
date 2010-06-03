
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pip.commands.search import compare_versions, highest_version, transform_hits
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

