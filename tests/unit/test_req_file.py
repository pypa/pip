from pretend import stub

from pip.req.req_install import InstallRequirement
from pip.req.req_file import (parse_requirement_options, parse_content,
                              parse_line, join_lines, ignore_comments,
                              partition_line, REQUIREMENT_EDITABLE, REQUIREMENT,
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
        assert 'req', '--option=value --flag' == partition_line('req --option=value --flag')


class TestJoinLines(object):
    """tests for `join_lines`"""

    def test_join_lines(self):
        lines = ['line1_begin \\', 'line1_end', 'line2']
        assert ['line1_begin line1_end', 'line2'] == list(join_lines(lines))


class TestParseRequirementOptions(object):
    """tests for `parse_requirement_options`"""

    def test_install_options_no_quotes(self):
        args = '--install-option --user'
        assert {'install_options': ['--user']} == parse_requirement_options(args)

    def test_install_options_quotes(self):
        args = "--install-option '--user'"
        assert {'install_options': ['--user']} == parse_requirement_options(args)

    def test_install_options_equals(self):
        args = "--install-option='--user'"
        assert {'install_options': ['--user']} == parse_requirement_options(args)

    def test_install_options_multiple(self):
        args = "--install-option='--user' --install-option='--root'"
        assert {'install_options': ['--user', '--root']} == parse_requirement_options(args)

    def test_install__global_options(self):
        args = "--install-option='--user' --global-option='--author'"
        result = {'global_options': ['--author'], 'install_options': ['--user']}
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
        assert parse_line('--index-url=url') == (OPTION, ('--index-url', 'url'))

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
        call = lambda req_url, finder, comes_from, options, session: [req]
        parse_requirements_stub = stub(call=call)
        monkeypatch.setattr(pip.req.req_file, 'parse_requirements', parse_requirements_stub.call)
        assert list(parse_content('filename', content)) == [req]


class TestParseRequirements(object):
    """tests for `parse_requirements`"""
    pass
