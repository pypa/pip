import pytest
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement

from pip._internal.models.link import Link
from pip._internal.req.parsing import (
    RequirementInfo,
    RequirementParsingError,
    convert_extras,
    looks_like_direct_reference,
    looks_like_path,
    looks_like_url,
    parse_requirement_text,
)
from pip._internal.utils.misc import path_to_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Set, Union


@pytest.mark.parametrize('text,expected', [
    ('[extra]', {'extra'}),
    ('[extra1,extra2]', {'extra1', 'extra2'}),
    ('', set()),
    (None, set()),
])
def test_convert_extras(text, expected):
    assert expected == convert_extras(text)


@pytest.mark.parametrize('text,expected', [
    ('example @ file://.', True),
    ('example@ https://.', True),
    ('https://.', False),
    ('https://git.example.com/repo@commit', False),
    ('https://user:pass@git.example.com/repo', False),
])
def test_looks_like_direct_reference(text, expected):
    assert expected == looks_like_direct_reference(text)


@pytest.mark.parametrize('text,expected', [
    ('/example/hello', True),
    ('hello', False),
    ('/example[extra]', True),
    ('.', True),
    ('.[extra]', True),
])
def test_looks_like_path(text, expected):
    assert expected == looks_like_path(text)


@pytest.mark.skipif('sys.platform != "win32"')
@pytest.mark.parametrize('text,expected', [
    ('C:\\Example', True),
    ('.\\', True),
])
def test_looks_like_path_windows(text, expected):
    assert expected == looks_like_path(expected)


@pytest.mark.parametrize('text,expected', [
    ('http://example.com/', True),
    ('./example', False),
])
def test_looks_like_url(text, expected):
    assert expected == looks_like_url(text)


def _assert_requirement(expected, test):
    # type: (Optional[Requirement], Optional[Requirement]) -> None
    if expected is None or test is None:
        assert expected == test
        return

    assert expected.name == test.name
    assert expected.specifier == test.specifier
    assert expected.url == test.url
    assert expected.extras == test.extras
    assert expected.marker == test.marker


def _assert_requirement_info(
    expected, test,
):
    # type: (RequirementInfo, RequirementInfo) -> None
    _assert_requirement(expected.requirement, test.requirement)
    assert (expected.link is None) == (test.link is None)
    if expected.link is not None:
        assert expected.link.url == test.link.url
    assert str(expected.markers) == str(test.markers)
    assert expected.extras == test.extras


INPUT = object()


def req_info(
    req=None,  # type: Optional[Union[str, object]]
    link=None,  # type: Optional[Union[str, object]]
    markers=None,  # type: Optional[str]
    extras=None,  # type: Optional[Set[str]]
):
    def get_req_info(text):
        _req = req
        if _req is INPUT:
            _req = text
        _link = link
        if _link is INPUT:
            _link = text

        return RequirementInfo(
            Requirement(_req) if _req else None,
            Link(_link) if _link else None,
            Marker(markers) if markers else None,
            set() if extras is None else extras,
        )

    return get_req_info


@pytest.mark.parametrize('text,make_expected', [
    ('.', req_info(link=path_to_url('.'))),
    ('.[extra1]', req_info(link=path_to_url('.'), extras={'extra1'})),
    ('path/to/project', req_info(link=path_to_url('path/to/project'))),

    ('pkg[extra1]', req_info(req=INPUT, extras={'extra1'})),

    ('https://github.com/a/b/c/asdf-1.5.2-cp27-none-xyz.whl'
     '; sys_platform == "xyz"',
     req_info(
         link='https://github.com/a/b/c/asdf-1.5.2-cp27-none-xyz.whl',
         markers='sys_platform == "xyz"',
     )),
    ('git+http://git.example.com/pkgrepo#egg=pkg',
     req_info(req='pkg', link=INPUT)),
    ('git+http://git.example.com/pkgrepo#egg=pkg[extra1]',
     req_info(req='pkg[extra1]', link=INPUT, extras={'extra1'})),
])
def test_parse_requirement_text(text, make_expected):
    _assert_requirement_info(
        parse_requirement_text(text), make_expected(text),
    )


@pytest.mark.parametrize('text,expected_message', [
    ('file:.', 'name-based'),
    ('@ http://example', 'direct reference'),
])
def test_parse_requirement_text_fail(text, expected_message):
    with pytest.raises(RequirementParsingError) as e:
        parse_requirement_text(text)
    assert expected_message in e.value.type_tried
