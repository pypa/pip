import os
import subprocess
from textwrap import dedent

from mock import patch
import pytest
from pretend import stub

from pip.exceptions import (RequirementsFileParseError,
                            ReqFileOnlyOneReqPerLineError,
                            ReqFileOnleOneOptionPerLineError,
                            ReqFileOptionNotAllowedWithReqError)
from pip.download import PipSession
from pip.index import PackageFinder
from pip.req.req_install import InstallRequirement
from pip.req.req_file import (parse_requirements, process_line, join_lines,
                              ignore_comments)


@pytest.fixture
def session():
    return PipSession()


@pytest.fixture
def finder(session):
    return PackageFinder([], [], session=session)


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


class TestProcessLine(object):
    """tests for `process_line`"""

    def setup(self):
        self.options = stub(isolated_mode=False, default_vcs=None,
                            skip_requirements_regex=False)

    def test_parser_error(self):
        with pytest.raises(RequirementsFileParseError):
            list(process_line("--bogus", "file", 1))

    def test_only_one_req_per_line(self):
        with pytest.raises(ReqFileOnlyOneReqPerLineError):
            list(process_line("req1 req2", "file", 1))

    def test_only_one_option_per_line(self):
        with pytest.raises(ReqFileOnleOneOptionPerLineError):
            list(process_line("--index-url=url --no-use-wheel", "file", 1))

    def test_option_not_allowed_on_req_line(self):
        with pytest.raises(ReqFileOptionNotAllowedWithReqError):
            list(process_line("req --index-url=url", "file", 1))

    def test_yield_line_requirement(self):
        line = 'SomeProject'
        filename = 'filename'
        comes_from = '-r %s (line %s)' % (filename, 1)
        req = InstallRequirement.from_line(line, comes_from=comes_from)
        assert repr(list(process_line(line, filename, 1))[0]) == repr(req)

    def test_yield_editable_requirement(self):
        url = 'git+https://url#egg=SomeProject'
        line = '-e %s' % url
        filename = 'filename'
        comes_from = '-r %s (line %s)' % (filename, 1)
        req = InstallRequirement.from_editable(url, comes_from=comes_from)
        assert repr(list(process_line(line, filename, 1))[0]) == repr(req)

    def test_nested_requirements_file(self, monkeypatch):
        line = '-r another_file'
        req = InstallRequirement.from_line('SomeProject')
        import pip.req.req_file

        def stub_parse_requirements(req_url, finder, comes_from, options,
                                    session, cache_root):
            return [req]
        parse_requirements_stub = stub(call=stub_parse_requirements)
        monkeypatch.setattr(pip.req.req_file, 'parse_requirements',
                            parse_requirements_stub.call)
        assert list(process_line(line, 'filename', 1)) == [req]

    def test_options_on_a_requirement_line(self):
        line = 'SomeProject --install-option=yo1 --install-option yo2 '\
               '--global-option="yo3" --global-option "yo4"'
        filename = 'filename'
        req = list(process_line(line, filename, 1))[0]
        assert req.options == {
            'global_options': ['yo3', 'yo4'],
            'install_options': ['yo1', 'yo2']}

    def test_set_isolated(self):
        line = 'SomeProject'
        filename = 'filename'
        self.options.isolated_mode = True
        result = process_line(line, filename, 1, options=self.options)
        assert list(result)[0].isolated

    def test_set_default_vcs(self):
        url = 'https://url#egg=SomeProject'
        line = '-e %s' % url
        filename = 'filename'
        self.options.default_vcs = 'git'
        result = process_line(line, filename, 1, options=self.options)
        assert list(result)[0].link.url == 'git+' + url

    def test_set_finder_no_index(self, finder):
        list(process_line("--no-index", "file", 1, finder=finder))
        assert finder.index_urls == []

    def test_set_finder_index_url(self, finder):
        list(process_line("--index-url=url", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_set_finder_find_links(self, finder):
        list(process_line("--find-links=url", "file", 1, finder=finder))
        assert finder.find_links == ['url']

    def test_set_finder_extra_index_urls(self, finder):
        list(process_line("--extra-index-url=url", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_set_finder_allow_external(self, finder):
        list(process_line("--allow-external=SomeProject",
                          "file", 1, finder=finder))
        assert finder.allow_external == set(['someproject'])

    def test_set_finder_allow_unsafe(self, finder):
        list(process_line("--allow-unverified=SomeProject",
                          "file", 1, finder=finder))
        assert finder.allow_unverified == set(['someproject'])

    def test_set_finder_use_wheel(self, finder):
        list(process_line("--use-wheel", "file", 1, finder=finder))
        assert finder.use_wheel is True

    def test_set_finder_no_use_wheel(self, finder):
        list(process_line("--no-use-wheel", "file", 1, finder=finder))
        assert finder.use_wheel is False

    def test_noop_always_unzip(self, finder):
        # noop, but confirm it can be set
        list(process_line("--always-unzip", "file", 1, finder=finder))

    def test_noop_finder_no_allow_unsafe(self, finder):
        # noop, but confirm it can be set
        list(process_line("--no-allow-insecure", "file", 1, finder=finder))


class TestOptionVariants(object):

    # this suite is really just testing optparse, but added it anyway

    def test_variant1(self, finder):
        list(process_line("-i url", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_variant2(self, finder):
        list(process_line("-i 'url'", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_variant3(self, finder):
        list(process_line("--index-url=url", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_variant4(self, finder):
        list(process_line("--index-url url", "file", 1, finder=finder))
        assert finder.index_urls == ['url']

    def test_variant5(self, finder):
        list(process_line("--index-url='url'", "file", 1, finder=finder))
        assert finder.index_urls == ['url']


class TestParseRequirements(object):
    """tests for `parse_requirements`"""

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

    def test_multiple_appending_options(self, tmpdir, finder):
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("--extra-index-url url1 \n")
            fp.write("--extra-index-url url2 ")

        list(parse_requirements(tmpdir.join("req1.txt"), finder=finder,
                                session=PipSession()))

        assert finder.index_urls == ['url1', 'url2']

    def test_skip_regex(self, tmpdir, finder):
        options = stub(isolated_mode=False, default_vcs=None,
                       skip_requirements_regex='.*Bad.*')
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("--extra-index-url Bad \n")
            fp.write("--extra-index-url Good ")

        list(parse_requirements(tmpdir.join("req1.txt"), finder=finder,
                                options=options, session=PipSession()))

        assert finder.index_urls == ['Good']

    def test_join_lines(self, tmpdir, finder):
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("--extra-index-url url1 \\\n--extra-index-url url2")

        list(parse_requirements(tmpdir.join("req1.txt"), finder=finder,
                                session=PipSession()))

        assert finder.index_urls == ['url1', 'url2']

    def test_req_file_parse_comment_start_of_line(self, tmpdir, finder):
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("# Comment ")

        reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                    session=PipSession()))

        assert not reqs

    def test_req_file_parse_comment_end_of_line_with_url(self, tmpdir, finder):
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("https://example.com/foo.tar.gz # Comment ")

        reqs = list(parse_requirements(tmpdir.join("req1.txt"), finder,
                    session=PipSession()))

        assert len(reqs) == 1
        assert reqs[0].link.url == "https://example.com/foo.tar.gz"

    def test_req_file_parse_egginfo_end_of_line_with_url(self, tmpdir, finder):
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.join("req1.txt"), "w") as fp:
            fp.write("https://example.com/foo.tar.gz#egg=wat")

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
        INITools==2.0 --global-option="{global_option}" \
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
