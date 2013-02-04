from textwrap import dedent
from tempfile import NamedTemporaryFile
from nose.tools import assert_equal, assert_raises

from pip.req_parser import *
from pip.index import PackageFinder


def test_line_continuations():
    test = '''\
    line 1
    line 2:1 \\
    line 2:2
    line 3:1 \\
     line 3:2 \\
      line 3:3'''

    expect = ['line 1', 'line 2:1 line 2:2', 'line 3:1  line 3:2   line 3:3']
    assert expect == list(join_lines(dedent(test).splitlines()))


def test_parse_simple_requirement():
    line = 'INITools==0.2'
    res = parse_line(line, 0, 't', opts=False)
    assert res == (REQUIREMENT, ('INITools==0.2', {}))

    # TODO: replace with next() if support for Py2.5 is dropped
    ireq = list(parse_content('t', line))[0]
    assert ireq.name == 'INITools'
    assert ireq.req.specs == [('==', '0.2')]


def test_parse_requirement_with_options():
    line = 'INITools==0.2 --install-options="--prefix=/opt" --global-options="--bindir=/usr/bin"'
    res = parse_line(line, 0, 't')
    assert res == (REQUIREMENT, ('INITools==0.2', {'install_options': '--prefix=/opt',
                                                   'global_options': '--bindir=/usr/bin'}))


def test_parse_editable_requirement():
    lines = ('--editable svn+https://foo#egg=foo',
             '--editable=svn+https://foo#egg=foo',
             '-e svn+https://foo#egg=foo')

    res = map_parse(lines)
    assert res == [(REQUIREMENT_EDITABLE, 'svn+https://foo#egg=foo')] * 3

    ireq = list(parse_content('t', lines[0]))[0]
    assert ireq.name == 'foo'
    assert ireq.url == 'svn+https://foo#egg=foo'


def test_parse_requirements_include():
    with NamedTemporaryFile() as fh:
        lines = ('-r %s' % fh.name,
                 '--requirement %s' % fh.name,
                 '--requirement=%s' % fh.name)

        res = map_parse(lines)
        assert res == [(REQUIREMENT_FILE, fh.name)] * 3

        fh.write('INITools==0.2\ndistribute\n')
        fh.flush()

        ireq = list(parse_content('t', lines[0]))
        assert len(ireq) == 2
        assert (ireq[0].name, ireq[1].name) == ('INITools', 'distribute')


def test_parse_find_links():
    lines = ('-f abc', '--find-links abc', '--find-links=abc')
    res = map_parse(lines)
    assert res == [(FINDLINKS, 'abc')] * 3

    finder = PackageFinder([], [])
    res = list(parse_content('t', lines[0], finder=finder))
    assert finder.find_links == ['abc']


def test_parse_index_url():
    lines = ('-i abc', '--index-url abc', '--index-url=abc')
    res = map_parse(lines)
    assert res == [(INDEXURL, 'abc')] * 3

    line = '--extra-index-url=123'
    res = parse_line(line, 0, 't')
    assert res == (EXTRAINDEXURL, '123')

    finder = PackageFinder([], [])
    res = list(parse_content('t', lines[0], finder=finder))
    res = list(parse_content('t', line, finder=finder))
    assert finder.index_urls == ['abc', '123']


def test_get_requirement_options():
    go = get_options
    opts = go('ign --aflag --bflag', ['--aflag', '--bflag'])
    assert opts == {'install_options': None, 'aflag': True, 'global_options': None, 'bflag': True}

    opts = go('ign --install-options="--abc --zxc"', [], ['--install-options'])
    assert opts == {'install_options': '--abc --zxc'}

    opts = go('ign --aflag --global-options="--abc" --install-options="--aflag"',
              ['--aflag'], ['--install-options', '--global-options'])
    assert opts == {'install_options': '--aflag', 'aflag': True, 'global_options': '--abc'}


def map_parse(lines):
    return list(map(lambda x: parse_line(x, 0, 't'), lines))
