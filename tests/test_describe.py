import pip.download
from pip.commands.describe import DescribeCommand
from pip.status_codes import NO_MATCHES_FOUND, SUCCESS
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
    env = reset_env(use_distribute=True)
    result = run_pip('describe', expect_error=True)
    assert 'ERROR: Missing required argument (search query).' in result.stdout


def test_reformat_data():
    """"
    Test reformat indents all lines after the first to the correct indentation
    """
    d = DescribeCommand()
    package = {'name': 'foo'*4, "version": "12.3"}
    d.reformat(package, 5, 10)
    assert "foofo\n     ofoof\n     oo" == package['name']
    assert "12.3" == package['version']

def test_update_package_info():
    """
    Test that updated information is stashed correctly
    """
    d = DescribeCommand()
    d._pypi = Mock()
    d._pypi.release_data = Mock()
    d._pypi.release_data.return_value = {
             'home_page': 'http://some.url',
             'package_url': 'http://another.url',
             'author': 'whodidit',
             'summary': 'short test data',
             'description': 'longer description about the test'
             }
    data = d.update_package_info([('name', '12')])
    assert len(data) == 1
    data = data[0]
    assert "name" == data['name']
    assert "12" == data['version']
    assert "http://some.url" == data['homepage']
    assert "http://another.url" == data['url']
    assert "whodidit" == data['author']
    assert "short test data" == data['summary']
    assert "longer description about the test" == data['description']

def test_packagename_is_case_insensitive():
    d = DescribeCommand()
    d._pypi = Mock()
    d._pypi.list_packages = Mock()
    d._pypi.list_packages.return_value=['asdf', 'foo', 'bar']
    d._pypi.package_releases = Mock()
    d._pypi.package_releases.return_value=["1", "2"]
    assert d.resolve_package('ASDF') == ('asdf', "2")
