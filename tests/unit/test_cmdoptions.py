import pretend
import pytest

from pip._internal.cli.cmdoptions import (
    _convert_python_version, make_search_scope,
)


@pytest.mark.parametrize(
    'no_index, suppress_no_index, expected_index_urls', [
        (False, False, ['default_url', 'url1', 'url2']),
        (False, True, ['default_url', 'url1', 'url2']),
        (True, False, []),
        # Passing suppress_no_index=True suppresses no_index=True.
        (True, True, ['default_url', 'url1', 'url2']),
    ],
)
def test_make_search_scope(no_index, suppress_no_index, expected_index_urls):
    """
    :param expected: the expected index_urls value.
    """
    options = pretend.stub(
        find_links=['link1'],
        index_url='default_url',
        extra_index_urls=['url1', 'url2'],
        no_index=no_index,
    )
    search_scope = make_search_scope(
        options, suppress_no_index=suppress_no_index,
    )
    assert search_scope.find_links == ['link1']
    assert search_scope.index_urls == expected_index_urls


@pytest.mark.parametrize('value, expected', [
    ('', (None, None)),
    ('2', ((2,), None)),
    ('3', ((3,), None)),
    ('3.7', ((3, 7), None)),
    ('3.7.3', ((3, 7, 3), None)),
    # Test strings without dots of length bigger than 1.
    ('34', ((3, 4), None)),
    # Test a 2-digit minor version.
    ('310', ((3, 10), None)),
    # Test some values that fail to parse.
    ('ab', ((), 'each version part must be an integer')),
    ('3a', ((), 'each version part must be an integer')),
    ('3.7.a', ((), 'each version part must be an integer')),
    ('3.7.3.1', ((), 'at most three version parts are allowed')),
])
def test_convert_python_version(value, expected):
    actual = _convert_python_version(value)
    assert actual == expected, 'actual: {!r}'.format(actual)
