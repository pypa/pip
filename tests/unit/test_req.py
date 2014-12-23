import os
import shutil
import sys
import tempfile

import pytest

from mock import Mock, patch, mock_open
from pip.exceptions import (
    PreviousBuildDirError, InvalidWheelFilename, UnsupportedWheel,
)
from pip.download import PipSession
from pip.index import PackageFinder
from pip.req import (InstallRequirement, RequirementSet,
                     Requirements, parse_requirements)
from pip.req.req_install import parse_editable
from pip.utils import read_text_file
from pip._vendor import pkg_resources
from tests.lib import assert_raises_regexp


class TestRequirementSet(object):
    """RequirementSet tests"""

    def setup(self):
        self.tempdir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def basic_reqset(self):
        return RequirementSet(
            build_dir=os.path.join(self.tempdir, 'build'),
            src_dir=os.path.join(self.tempdir, 'src'),
            download_dir=None,
            session=PipSession(),
        )

    def test_no_reuse_existing_build_dir(self, data):
        """Test prepare_files raise exception with previous build dir"""

        build_dir = os.path.join(self.tempdir, 'build', 'simple')
        os.makedirs(build_dir)
        open(os.path.join(build_dir, "setup.py"), 'w')
        reqset = self.basic_reqset()
        req = InstallRequirement.from_line('simple')
        reqset.add_requirement(req)
        finder = PackageFinder([data.find_links], [], session=PipSession())
        assert_raises_regexp(
            PreviousBuildDirError,
            "pip can't proceed with [\s\S]*%s[\s\S]*%s" %
            (req, build_dir.replace('\\', '\\\\')),
            reqset.prepare_files,
            finder,
        )

    def test_environment_marker_extras(self, data):
        """
        Test that the environment marker extras are used with
        non-wheel installs.
        """
        reqset = self.basic_reqset()
        req = InstallRequirement.from_editable(
            data.packages.join("LocalEnvironMarker"))
        reqset.add_requirement(req)
        finder = PackageFinder([data.find_links], [], session=PipSession())
        reqset.prepare_files(finder)
        # This is hacky but does test both case in py2 and py3
        if sys.version_info[:2] in ((2, 7), (3, 4)):
            assert reqset.has_requirement('simple')
        else:
            assert not reqset.has_requirement('simple')


@pytest.mark.parametrize(('file_contents', 'expected'), [
    (b'\xf6\x80', b'\xc3\xb6\xe2\x82\xac'),  # cp1252
    (b'\xc3\xb6\xe2\x82\xac', b'\xc3\xb6\xe2\x82\xac'),  # utf-8
    (b'\xc3\xb6\xe2', b'\xc3\x83\xc2\xb6\xc3\xa2'),  # Garbage
])
def test_egg_info_data(file_contents, expected):
    om = mock_open(read_data=file_contents)
    em = Mock()
    em.return_value = 'cp1252'
    with patch('pip.utils.open', om, create=True):
        with patch('locale.getpreferredencoding', em):
            ret = read_text_file('foo')
    assert ret == expected.decode('utf-8')


class TestInstallRequirement(object):

    def test_url_with_query(self):
        """InstallRequirement should strip the fragment, but not the query."""
        url = 'http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz'
        fragment = '#egg=bar'
        req = InstallRequirement.from_line(url + fragment)
        assert req.url == url + fragment, req.url

    def test_unsupported_wheel_requirement_raises(self):
        with pytest.raises(UnsupportedWheel):
            InstallRequirement.from_line(
                'peppercorn-0.4-py2.py3-bogus-any.whl',
            )

    def test_installed_version_not_installed(self):
        req = InstallRequirement.from_line('simple-0.1-py2.py3-none-any.whl')
        assert req.installed_version is None

    def test_invalid_wheel_requirement_raises(self):
        with pytest.raises(InvalidWheelFilename):
            InstallRequirement.from_line('invalid.whl')

    def test_wheel_requirement_sets_req_attribute(self):
        req = InstallRequirement.from_line('simple-0.1-py2.py3-none-any.whl')
        assert req.req == pkg_resources.Requirement.parse('simple==0.1')

    def test_url_preserved_line_req(self):
        """Confirm the url is preserved in a non-editable requirement"""
        url = 'git+http://foo.com@ref#egg=foo'
        req = InstallRequirement.from_line(url)
        assert req.url == url

    def test_url_preserved_editable_req(self):
        """Confirm the url is preserved in a editable requirement"""
        url = 'git+http://foo.com@ref#egg=foo'
        req = InstallRequirement.from_editable(url)
        assert req.url == url

    def test_markers(self):
        for line in (
            # recommanded syntax
            'mock3; python_version >= "3"',
            # with more spaces
            'mock3 ; python_version >= "3" ',
            # without spaces
            'mock3;python_version >= "3"',
        ):
            req = InstallRequirement.from_line(line)
            assert req.req.project_name == 'mock3'
            assert req.req.specs == []
            assert req.markers == 'python_version >= "3"'

    def test_markers_semicolon(self):
        # check that the markers can contain a semicolon
        req = InstallRequirement.from_line('semicolon; os_name == "a; b"')
        assert req.req.project_name == 'semicolon'
        assert req.req.specs == []
        assert req.markers == 'os_name == "a; b"'

    def test_markers_url(self):
        # test "URL; markers" syntax
        url = 'http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz'
        line = '%s; python_version >= "3"' % url
        req = InstallRequirement.from_line(line)
        assert req.url == url, req.url
        assert req.markers == 'python_version >= "3"'

        # without space, markers are part of the URL
        url = 'http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz'
        line = '%s;python_version >= "3"' % url
        req = InstallRequirement.from_line(line)
        assert req.url == line, req.url
        assert req.markers is None

    def test_markers_match(self):
        # match
        for markers in (
            'python_version >= "1.0"',
            'sys_platform == %r' % sys.platform,
        ):
            line = 'name; ' + markers
            req = InstallRequirement.from_line(line)
            assert req.markers == markers
            assert req.match_markers()

        # don't match
        for markers in (
            'python_version >= "5.0"',
            'sys_platform != %r' % sys.platform,
        ):
            line = 'name; ' + markers
            req = InstallRequirement.from_line(line)
            assert req.markers == markers
            assert not req.match_markers()


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
@patch('pip.req.req_install.os.getcwd')
@patch('pip.req.req_install.os.path.exists')
@patch('pip.req.req_install.os.path.isdir')
def test_parse_editable_local(
        isdir_mock, exists_mock, getcwd_mock, normcase_mock):
    exists_mock.return_value = isdir_mock.return_value = True
    # mocks needed to support path operations on windows tests
    normcase_mock.return_value = getcwd_mock.return_value = "/some/path"
    assert parse_editable('.', 'git') == (None, 'file:///some/path', None, {})
    normcase_mock.return_value = "/some/path/foo"
    assert parse_editable('foo', 'git') == (
        None, 'file:///some/path/foo', None, {},
    )


def test_parse_editable_default_vcs():
    assert parse_editable('https://foo#egg=foo', 'git') == (
        'foo',
        'git+https://foo#egg=foo',
        None,
        {'egg': 'foo'},
    )


def test_parse_editable_explicit_vcs():
    assert parse_editable('svn+https://foo#egg=foo', 'git') == (
        'foo',
        'svn+https://foo#egg=foo',
        None,
        {'egg': 'foo'},
    )


def test_parse_editable_vcs_extras():
    assert parse_editable('svn+https://foo#egg=foo[extras]', 'git') == (
        'foo[extras]',
        'svn+https://foo#egg=foo[extras]',
        None,
        {'egg': 'foo[extras]'},
    )


@patch('os.path.normcase')
@patch('pip.req.req_install.os.getcwd')
@patch('pip.req.req_install.os.path.exists')
@patch('pip.req.req_install.os.path.isdir')
def test_parse_editable_local_extras(
        isdir_mock, exists_mock, getcwd_mock, normcase_mock):
    exists_mock.return_value = isdir_mock.return_value = True
    normcase_mock.return_value = getcwd_mock.return_value = "/some/path"
    assert parse_editable('.[extras]', 'git') == (
        None, 'file://' + "/some/path", ('extras',), {},
    )
    normcase_mock.return_value = "/some/path/foo"
    assert parse_editable('foo[bar,baz]', 'git') == (
        None, 'file:///some/path/foo', ('bar', 'baz'), {},
    )


def test_remote_reqs_parse():
    """
    Test parsing a simple remote requirements file
    """
    # this requirements file just contains a comment
    # previously this has failed in py3: https://github.com/pypa/pip/issues/760
    for req in parse_requirements(
            'https://raw.githubusercontent.com/pypa/pip-test-package/master/'
            'tests/req_just_comment.txt', session=PipSession()):
        pass


def test_req_file_parse_no_use_wheel(data):
    """
    Test parsing --no-use-wheel from a req file
    """
    finder = PackageFinder([], [], session=PipSession())
    for req in parse_requirements(
            data.reqfiles.join("supported_options.txt"), finder,
            session=PipSession()):
        pass
    assert not finder.use_wheel


def test_req_file_parse_comment_start_of_line(tmpdir):
    """
    Test parsing comments in a requirements file
    """
    with open(tmpdir.join("req1.txt"), "w") as fp:
        fp.write("# Comment ")

    finder = PackageFinder([], [], session=PipSession())
    reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                session=PipSession()))

    assert not reqs


def test_req_file_parse_comment_end_of_line_with_url(tmpdir):
    """
    Test parsing comments in a requirements file
    """
    with open(tmpdir.join("req1.txt"), "w") as fp:
        fp.write("https://example.com/foo.tar.gz # Comment ")

    finder = PackageFinder([], [], session=PipSession())
    reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                session=PipSession()))

    assert len(reqs) == 1
    assert reqs[0].url == "https://example.com/foo.tar.gz"


def test_req_file_parse_egginfo_end_of_line_with_url(tmpdir):
    """
    Test parsing comments in a requirements file
    """
    with open(tmpdir.join("req1.txt"), "w") as fp:
        fp.write("https://example.com/foo.tar.gz#egg=wat")

    finder = PackageFinder([], [], session=PipSession())
    reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                session=PipSession()))

    assert len(reqs) == 1
    assert reqs[0].name == "wat"


def test_req_file_no_finder(tmpdir):
    """
    Test parsing a requirements file without a finder
    """
    with open(tmpdir.join("req.txt"), "w") as fp:
        fp.write("""
--find-links https://example.com/
--index-url https://example.com/
--extra-index-url https://two.example.com/
--no-use-wheel
--no-index
--allow-external foo
--allow-all-external
--allow-insecure foo
--allow-unverified foo
        """)

    parse_requirements(tmpdir.join("req.txt"), session=PipSession())
