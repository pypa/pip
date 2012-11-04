import os.path
import textwrap
from nose.tools import assert_equal, assert_raises
from mock import patch
from pip.backwardcompat import urllib
from pip.req import Requirements, parse_editable
from tests.test_pip import reset_env, run_pip, write_file, pyversion, here, path_to_url
from tests.local_repos import local_checkout
from tests.path import Path


def test_requirements_file():
    """
    Test installing from a requirements file.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert env.site_packages/'INITools-0.2-py%s.egg-info' % pyversion in result.files_created
    assert env.site_packages/'initools' in result.files_created
    assert result.files_created[env.site_packages/other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[env.site_packages/fn].dir


def test_schema_check_in_requirements_file():
    """
    Test installing from a requirements file with an invalid vcs schema..

    """
    env = reset_env()
    write_file('file-egg-req.txt', textwrap.dedent("""\
        git://github.com/alex/django-fixture-generator.git#egg=fixture_generator
        """))
    assert_raises(AssertionError, run_pip, 'install', '-vvv', '-r', env.scratch_path / 'file-egg-req.txt')


def test_relative_requirements_file():
    """
    Test installing from a requirements file with a relative path with an egg= definition..

    """
    url = path_to_url(os.path.join(here, 'packages', '..', 'packages', 'FSPkg')) + '#egg=FSPkg'
    env = reset_env()
    write_file('file-egg-req.txt', textwrap.dedent("""\
        %s
        """ % url))
    result = run_pip('install', '-vvv', '-r', env.scratch_path / 'file-egg-req.txt')
    assert (env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)
    assert (env.site_packages/'fspkg') in result.files_created, str(result.stdout)


def test_multiple_requirements_files():
    """
    Test installing from multiple nested requirements files.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        -e %s@10#egg=INITools-dev
        -r %s-req.txt""" % (local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                            other_lib_name)))
    write_file('%s-req.txt' % other_lib_name, textwrap.dedent("""\
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert result.files_created[env.site_packages/other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[env.site_packages/fn].dir
    assert env.venv/'src'/'initools' in result.files_created


def test_respect_order_in_requirements_file():
    env = reset_env()
    write_file('frameworks-req.txt', textwrap.dedent("""\
        parent
        child
        simple
        """))

    find_links = 'file://' + os.path.join(here, 'packages')
    result = run_pip('install', '--no-index', '-f', find_links, '-r', env.scratch_path / 'frameworks-req.txt')

    downloaded = [line for line in result.stdout.split('\n')
                  if 'Downloading/unpacking' in line]

    assert 'parent' in downloaded[0], 'First download should ' \
            'be "parent" but was "%s"' % downloaded[0]
    assert 'child' in downloaded[1], 'Second download should ' \
            'be "child" but was "%s"' % downloaded[1]
    assert 'simple' in downloaded[2], 'Third download should ' \
            'be "simple" but was "%s"' % downloaded[2]


def test_requirements_data_structure_keeps_order():
    requirements = Requirements()
    requirements['pip'] = 'pip'
    requirements['nose'] = 'nose'
    requirements['coverage'] = 'coverage'

    assert ['pip', 'nose', 'coverage'] == list(requirements.values())
    assert ['pip', 'nose', 'coverage'] == list(requirements.keys())


def test_requirements_data_structure_implements__repr__():
    requirements = Requirements()
    requirements['pip'] = 'pip'
    requirements['nose'] = 'nose'

    assert "Requirements({'pip': 'pip', 'nose': 'nose'})" == repr(requirements)


def test_requirements_data_structure_implements__contains__():
    requirements = Requirements()
    requirements['pip'] = 'pip'

    assert 'pip' in requirements
    assert 'nose' not in requirements

@patch('os.path.normcase')
@patch('pip.req.os.getcwd')
@patch('pip.req.os.path.exists')
@patch('pip.req.os.path.isdir')
def test_parse_editable_local(isdir_mock, exists_mock, getcwd_mock, normcase_mock):
    exists_mock.return_value = isdir_mock.return_value = True
    # mocks needed to support path operations on windows tests
    normcase_mock.return_value = getcwd_mock.return_value = "/some/path"
    assert_equal(
        parse_editable('.', 'git'),
        (None, 'file:///some/path', None)
    )
    normcase_mock.return_value = "/some/path/foo"
    assert_equal(
        parse_editable('foo', 'git'),
        (None, 'file:///some/path/foo', None)
    )

def test_parse_editable_default_vcs():
    assert_equal(
        parse_editable('https://foo#egg=foo', 'git'),
        ('foo', 'git+https://foo#egg=foo', None)
    )

def test_parse_editable_explicit_vcs():
    assert_equal(
        parse_editable('svn+https://foo#egg=foo', 'git'),
        ('foo', 'svn+https://foo#egg=foo', None)
    )

def test_parse_editable_vcs_extras():
    assert_equal(
        parse_editable('svn+https://foo#egg=foo[extras]', 'git'),
        ('foo[extras]', 'svn+https://foo#egg=foo[extras]', None)
    )

@patch('os.path.normcase')
@patch('pip.req.os.getcwd')
@patch('pip.req.os.path.exists')
@patch('pip.req.os.path.isdir')
def test_parse_editable_local_extras(isdir_mock, exists_mock, getcwd_mock, normcase_mock):
    exists_mock.return_value = isdir_mock.return_value = True
    normcase_mock.return_value = getcwd_mock.return_value = "/some/path"
    assert_equal(
        parse_editable('.[extras]', 'git'),
        (None, 'file://' + "/some/path", ('extras',))
    )
    normcase_mock.return_value = "/some/path/foo"
    assert_equal(
        parse_editable('foo[bar,baz]', 'git'),
        (None, 'file:///some/path/foo', ('bar', 'baz'))
    )

def test_install_local_editable_with_extras():
    env = reset_env()
    to_install = os.path.abspath(os.path.join(here, 'packages', 'LocalExtras'))
    res = run_pip('install', '-e', to_install + '[bar]', expect_error=False)
    assert env.site_packages/'easy-install.pth' in res.files_updated
    assert env.site_packages/'LocalExtras.egg-link' in res.files_created
    assert env.site_packages/'simple' in res.files_created
