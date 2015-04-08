import os
import subprocess
from textwrap import dedent

from mock import patch
import pytest
from pretend import stub

from pip.download import PipSession
from pip.index import PackageFinder
from pip.req.req_install import InstallRequirement
from pip.req.req_file import (parse_requirement_options, parse_content,
                              parse_requirements, parse_line, join_lines,
                              ignore_comments, partition_line,
                              REQUIREMENT_EDITABLE, REQUIREMENT,
                              REQUIREMENT_FILE, FLAG, OPTION, IGNORE)


class TestIgnoreComments(object):
    """tests for `ignore_comment`"""

    def test_strip_empty_line(self):
        lines = ['req1', '', 'req2']
        result = ignore_comments(lines)
        assert list(result) == ['req1', 'req2']

    def test_strip_comment(self):
        lines = ['req1', '# comment', 'req2']
        result = ignore_comments(lines)
        assert list(result) == ['req1', 'req2']


class TestPartitionLine(object):
    """tests for `partition_line`"""

    def test_split_req(self):
        assert 'req', '' == partition_line('req')

    def test_split_req_with_flag(self):
        assert 'req', '--flag' == partition_line('req --flag')

    def test_split_req_with_option_space(self):
        assert 'req', '--option value' == partition_line('req --option value')

    def test_split_req_with_option_equal(self):
        assert 'req', '--option=value' == partition_line('req --option=value')

    def test_split_req_with_option_and_flag(self):
        assert 'req', '--option=value --flag' == \
            partition_line('req --option=value --flag')


class TestJoinLines(object):
    """tests for `join_lines`"""

    def test_join_lines(self):
        lines = dedent('''\
        line 1
        line 2:1 \\
        line 2:2
        line 3:1 \\
        line 3:2 \\
        line 3:3
        line 4
        ''').splitlines()

        expect = [
            'line 1',
            'line 2:1 line 2:2',
            'line 3:1 line 3:2 line 3:3',
            'line 4',
        ]
        assert expect == list(join_lines(lines))


class TestParseRequirementOptions(object):
    """tests for `parse_requirement_options`"""

    def test_install_options_no_quotes(self):
        args = '--install-option --user'
        assert {'install_options': ['--user']} == \
            parse_requirement_options(args)

    def test_install_options_quotes(self):
        args = "--install-option '--user'"
        assert {'install_options': ['--user']} == \
            parse_requirement_options(args)

    def test_install_options_equals(self):
        args = "--install-option='--user'"
        assert {'install_options': ['--user']} == \
            parse_requirement_options(args)

    def test_install_options_with_spaces(self):
        args = "--install-option='--arg=value1 value2 value3'"
        assert {'install_options': ['--arg=value1 value2 value3']} == \
            parse_requirement_options(args)

    def test_install_options_multiple(self):
        args = "--install-option='--user' --install-option='--root'"
        assert {'install_options': ['--user', '--root']} == \
            parse_requirement_options(args)

    def test_install_and_global_options(self):
        args = "--install-option='--user' --global-option='--author'"
        result = {'global_options': ['--author'],
                  'install_options': ['--user']}
        assert result == parse_requirement_options(args)


class TestParseLine(object):
    """tests for `parse_line`"""

    # TODO
    # parser error tests

    def test_parse_line_editable(self):
        assert parse_line('-e url') == (REQUIREMENT_EDITABLE, 'url')
        assert parse_line('--editable url') == (REQUIREMENT_EDITABLE, 'url')

    def test_parse_line_req_file(self):
        assert parse_line('-r file') == (REQUIREMENT_FILE, 'file')
        assert parse_line('--requirement file') == (REQUIREMENT_FILE, 'file')

    def test_parse_line_flag(self):
        assert parse_line('--no-index') == (FLAG, '--no-index')

    def test_parse_line_option(self):
        result = (OPTION, ('--index-url', 'url'))
        assert parse_line('--index-url=url') == result
        assert parse_line('--index-url  =  url') == result
        assert parse_line('--index-url url') == result
        result = (OPTION, ('-i', 'url'))
        assert parse_line('-i=url') == result
        assert parse_line('-i  =  url') == result
        assert parse_line('-i url') == result

    def test_parse_line_ignore(self):
        assert parse_line('--use-wheel') == (IGNORE, '--use-wheel')

    def test_parse_line_requirement(self):
        assert parse_line('SomeProject') == (REQUIREMENT, ('SomeProject', {}))

    def test_parse_line_requirement_with_options(self):
        assert parse_line('SomeProject --install-option --user') == (
            REQUIREMENT,
            ('SomeProject', {'install_options': ['--user']})
        )


class TestParseContent(object):
    """tests for `parse_content`"""

    # TODO
    # isolated mode
    # comments
    # finder options
    # join
    # comes_from

    def test_parse_content_requirement(self):
        content = 'SomeProject'
        filename = 'filename'
        comes_from = '-r %s (line %s)' % (filename, 1)
        req = InstallRequirement.from_line(content, comes_from=comes_from)
        assert repr(list(parse_content(filename, content))[0]) == repr(req)

    def test_parse_content_editable(self):
        url = 'git+https://url#egg=SomeProject'
        content = '-e %s' % url
        filename = 'filename'
        comes_from = '-r %s (line %s)' % (filename, 1)
        req = InstallRequirement.from_editable(url, comes_from=comes_from)
        assert repr(list(parse_content(filename, content))[0]) == repr(req)

    def test_parse_content_requirements_file(self, monkeypatch):
        content = '-r another_file'
        req = InstallRequirement.from_line('SomeProject')
        import pip.req.req_file

        def stub_parse_requirements(req_url, finder, comes_from, options,
                                    session):
            return [req]
        parse_requirements_stub = stub(call=stub_parse_requirements)
        monkeypatch.setattr(pip.req.req_file, 'parse_requirements',
                            parse_requirements_stub.call)
        assert list(parse_content('filename', content)) == [req]


@pytest.fixture
def session():
    return PipSession()


@pytest.fixture
def finder(session):
    return PackageFinder([], [], session=session)


class TestParseRequirements(object):
    """tests for `parse_requirements`"""

    # TODO some of these test are replaced by tests in classes above

    @pytest.mark.network
    def test_remote_reqs_parse(self):
        """
        Test parsing a simple remote requirements file
        """
        # this requirements file just contains a comment previously this has
        # failed in py3: https://github.com/pypa/pip/issues/760
        for req in parse_requirements(
                'https://raw.githubusercontent.com/pypa/'
                'pip-test-package/master/'
                'tests/req_just_comment.txt', session=PipSession()):
            pass

    def test_req_file_parse_no_use_wheel(self, data):
        """
        Test parsing --no-use-wheel from a req file
        """
        finder = PackageFinder([], [], session=PipSession())
        for req in parse_requirements(
                data.reqfiles.join("supported_options.txt"), finder,
                session=PipSession()):
            pass
        assert not finder.use_wheel

    def test_req_file_parse_comment_start_of_line(self, tmpdir):
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("# Comment ")

        finder = PackageFinder([], [], session=PipSession())
        reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                    session=PipSession()))

        assert not reqs

    def test_req_file_parse_comment_end_of_line_with_url(self, tmpdir):
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("https://example.com/foo.tar.gz # Comment ")

        finder = PackageFinder([], [], session=PipSession())
        reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                    session=PipSession()))

        assert len(reqs) == 1
        assert reqs[0].link.url == "https://example.com/foo.tar.gz"

    def test_req_file_parse_egginfo_end_of_line_with_url(self, tmpdir):
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

    def test_req_file_no_finder(self, tmpdir):
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

    def test_install_requirements_with_options(self, tmpdir, finder, session):
        global_option = '--dry-run'
        install_option = '--prefix=/opt'

        content = '''
        INITools == 2.0 --global-option="{global_option}" \
                        --install-option "{install_option}"
        '''.format(global_option=global_option, install_option=install_option)

        req_path = tmpdir.join('requirements.txt')
        with open(req_path, 'w') as fh:
            fh.write(content)

        req = next(parse_requirements(req_path, finder=finder,
                                      session=session))

        req.source_dir = os.curdir
        with patch.object(subprocess, 'Popen') as popen:
            try:
                req.install([])
            except:
                pass

            call = popen.call_args_list[0][0][0]
            assert call.index(install_option) > \
                call.index('install') > \
                call.index(global_option) > 0
