"""
Tests for the describe command
"""
from pip.commands.describe import DescribeCommand
from mock import Mock
from tests.test_pip import run_pip, reset_env, pyversion

if pyversion >= '3':
    VERBOSE_FALSE = False
else:
    VERBOSE_FALSE = 0


def test_search_missing_argument():
    """
    Test missing required argument for describe
    """
    reset_env(use_distribute=True)
    result = run_pip('describe', expect_error=True)
    assert 'ERROR: Missing required argument (search query).' in result.stdout


def test_reformat_data():
    """"
    Test reformat indents all lines after the first to the correct indentation
    """
    desc_command = DescribeCommand()
    package = {'name': 'foo'*4, "version": "12.3"}
    desc_command.reformat(package, 5, 10)
    assert "foofo\n     ofoof\n     oo" == package['name']
    assert "12.3" == package['version']

def test_update_package_info():
    """
    Test that updated information is stashed correctly
    """
    desc_command = DescribeCommand()
    pipy_mock = Mock()
    pipy_mock.release_data = Mock()
    pipy_mock.release_data.return_value = {
             'home_page': 'http://some.url',
             'package_url': 'http://another.url',
             'author': 'whodidit',
             'summary': 'short test data',
             'description': 'longer description about the test'
             }
    desc_command._pypi = pipy_mock
    data = desc_command.update_package_info([('name', '12')])
    assert len(data) == 1
    data = data[0]
    assert "name" == data['name']
    assert "12" == data['version']
    assert "http://some.url" == data['homepage']
    assert "http://another.url" == data['url']
    assert "whodidit" == data['author']
    assert "short test data" == data['summary']
    assert "longer description about the test" == data['description']

def test_name_is_case_insensitive():
    """
    Test that packages are looked for in a case insensitive matter
    """
    desc_command = DescribeCommand()
    pypi_mock = Mock()
    pypi_mock.list_packages = Mock()
    pypi_mock.list_packages.return_value = ['asdf', 'foo', 'bar']
    pypi_mock.package_releases = Mock()
    pypi_mock.package_releases.return_value = ["1", "2"]
    desc_command._pypi = pypi_mock
    assert desc_command.resolve_package('ASDF') == ('asdf', "2")
