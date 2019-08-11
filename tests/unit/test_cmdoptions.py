import os

import pretend
import pytest
from mock import patch

from pip._internal.cli.cmdoptions import (
    _convert_python_version,
    make_search_scope,
)


@pytest.mark.parametrize(
    'find_links, no_index, suppress_no_index, expected', [
        (['link1'], False, False,
         (['link1'], ['default_url', 'url1', 'url2'])),
        (['link1'], False, True, (['link1'], ['default_url', 'url1', 'url2'])),
        (['link1'], True, False, (['link1'], [])),
        # Passing suppress_no_index=True suppresses no_index=True.
        (['link1'], True, True, (['link1'], ['default_url', 'url1', 'url2'])),
        # Test options.find_links=False.
        (False, False, False, ([], ['default_url', 'url1', 'url2'])),
    ],
)
def test_make_search_scope(find_links, no_index, suppress_no_index, expected):
    """
    :param expected: the expected (find_links, index_urls) values.
    """
    expected_find_links, expected_index_urls = expected
    options = pretend.stub(
        find_links=find_links,
        index_url='default_url',
        extra_index_urls=['url1', 'url2'],
        no_index=no_index,
    )
    search_scope = make_search_scope(
        options, suppress_no_index=suppress_no_index,
    )
    assert search_scope.find_links == expected_find_links
    assert search_scope.index_urls == expected_index_urls


@patch('pip._internal.utils.misc.expanduser')
def test_make_search_scope__find_links_expansion(mock_expanduser, tmpdir):
    """
    Test "~" expansion in --find-links paths.
    """
    # This is a mock version of expanduser() that expands "~" to the tmpdir.
    def expand_path(path):
        if path.startswith('~/'):
            path = os.path.join(tmpdir, path[2:])
        return path

    mock_expanduser.side_effect = expand_path

    options = pretend.stub(
        find_links=['~/temp1', '~/temp2'],
        index_url='default_url',
        extra_index_urls=[],
        no_index=False,
    )
    # Only create temp2 and not temp1 to test that "~" expansion only occurs
    # when the directory exists.
    temp2_dir = os.path.join(tmpdir, 'temp2')
    os.mkdir(temp2_dir)

    search_scope = make_search_scope(options)

    # Only ~/temp2 gets expanded. Also, the path is normalized when expanded.
    expected_temp2_dir = os.path.normcase(temp2_dir)
    assert search_scope.find_links == ['~/temp1', expected_temp2_dir]
    assert search_scope.index_urls == ['default_url']


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
