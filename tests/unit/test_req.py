import os
import shutil
import tempfile

from pkg_resources import Distribution
from mock import Mock, patch
from nose.tools import assert_equal, assert_raises
from pip.exceptions import PreviousBuildDirError
from pip.index import PackageFinder
from pip.log import logger
from pip.req import (InstallRequirement, RequirementSet, parse_editable,
                     Requirements, parse_requirements)
from tests.lib import path_to_url, assert_raises_regexp, find_links, tests_data


class TestRequirementSet(object):
    """RequirementSet tests"""

    def setup(self):
        logger.consumers = [(logger.NOTIFY, Mock())]
        self.tempdir = tempfile.mkdtemp()

    def teardown(self):
        logger.consumers = []
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def basic_reqset(self):
        return RequirementSet(
            build_dir=os.path.join(self.tempdir, 'build'),
            src_dir=os.path.join(self.tempdir, 'src'),
            download_dir=None,
            download_cache=os.path.join(self.tempdir, 'download_cache')
            )

    def test_no_reuse_existing_build_dir(self):
        """Test prepare_files raise exception with previous build dir"""

        build_dir = os.path.join(self.tempdir, 'build', 'simple')
        os.makedirs(build_dir)
        open(os.path.join(build_dir, "setup.py"), 'w')
        reqset = self.basic_reqset()
        req = InstallRequirement.from_line('simple')
        reqset.add_requirement(req)
        finder = PackageFinder([find_links], [])
        assert_raises_regexp(
            PreviousBuildDirError,
            "pip can't proceed with [\s\S]*%s[\s\S]*%s" % (req, build_dir.replace('\\', '\\\\')),
            reqset.prepare_files,
            finder
            )


def test_url_with_query():
    """InstallRequirement should strip the fragment, but not the query."""
    url = 'http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz'
    fragment = '#egg=bar'
    req = InstallRequirement.from_line(url + fragment)

    assert req.url == url, req.url


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

def test_remote_reqs_parse():
    """
    Test parsing a simple remote requirements file
    """
    # this requirements file just contains a comment
    # previously this has failed in py3 (https://github.com/pypa/pip/issues/760)
    for req in parse_requirements('https://raw.github.com/pypa/pip-test-package/master/tests/req_just_comment.txt'):
        pass

# patch this for travis which has distribute in it's base env for now
@patch('pip.wheel.pkg_resources.get_distribution', lambda x: Distribution(project_name='setuptools', version='0.9'))
def test_req_file_parse_use_wheel():
    """
    Test parsing --use-wheel from a req file
    """
    reqfile = os.path.join(tests_data, 'reqfiles', 'supported_options.txt')
    finder = PackageFinder([], [])
    for req in parse_requirements(reqfile, finder):
        pass
    assert finder.use_wheel
