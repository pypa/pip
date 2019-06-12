import logging
import os.path

import pytest
from mock import Mock
from pip._vendor import html5lib, requests

from pip._internal.download import PipSession
from pip._internal.index import (
    CandidateEvaluator, Link, PackageFinder, Search,
    _check_link_requires_python, _clean_link, _determine_base_url,
    _egg_info_matches, _find_name_version_sep, _get_html_page,
)
from pip._internal.models.target_python import TargetPython
from tests.lib import CURRENT_PY_VERSION_INFO


@pytest.mark.parametrize('requires_python, expected', [
    ('== 3.6.4', False),
    ('== 3.6.5', True),
    # Test an invalid Requires-Python value.
    ('invalid', True),
])
def test_check_link_requires_python(requires_python, expected):
    version_info = (3, 6, 5)
    link = Link('https://example.com', requires_python=requires_python)
    actual = _check_link_requires_python(link, version_info)
    assert actual == expected


def check_caplog(caplog, expected_level, expected_message):
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == expected_level
    assert record.message == expected_message


@pytest.mark.parametrize('ignore_requires_python, expected', [
    (None, (
        False, 'DEBUG',
        "Link requires a different Python (3.6.5 not in: '== 3.6.4'): "
        "https://example.com"
    )),
    (True, (
        True, 'DEBUG',
        "Ignoring failed Requires-Python check (3.6.5 not in: '== 3.6.4') "
        "for link: https://example.com"
    )),
])
def test_check_link_requires_python__incompatible_python(
    caplog, ignore_requires_python, expected,
):
    """
    Test an incompatible Python.
    """
    expected_return, expected_level, expected_message = expected
    link = Link('https://example.com', requires_python='== 3.6.4')
    caplog.set_level(logging.DEBUG)
    actual = _check_link_requires_python(
        link, version_info=(3, 6, 5),
        ignore_requires_python=ignore_requires_python,
    )
    assert actual == expected_return

    check_caplog(caplog, expected_level, expected_message)


def test_check_link_requires_python__invalid_requires(caplog):
    """
    Test the log message for an invalid Requires-Python.
    """
    link = Link('https://example.com', requires_python='invalid')
    caplog.set_level(logging.DEBUG)
    actual = _check_link_requires_python(link, version_info=(3, 6, 5))
    assert actual

    expected_message = (
        "Ignoring invalid Requires-Python ('invalid') for link: "
        "https://example.com"
    )
    check_caplog(caplog, 'DEBUG', expected_message)


class TestCandidateEvaluator:

    def test_init__target_python(self):
        """
        Test the target_python argument.
        """
        target_python = TargetPython(py_version_info=(3, 7, 3))
        evaluator = CandidateEvaluator(target_python=target_python)
        # The target_python attribute should be set as is.
        assert evaluator._target_python is target_python

    def test_init__target_python_none(self):
        """
        Test passing None for the target_python argument.
        """
        evaluator = CandidateEvaluator(target_python=None)
        # Spot-check the default TargetPython object.
        actual_target_python = evaluator._target_python
        assert actual_target_python._given_py_version_info is None
        assert actual_target_python.py_version_info == CURRENT_PY_VERSION_INFO

    @pytest.mark.parametrize(
        'py_version_info,ignore_requires_python,expected', [
            ((3, 6, 5), None, (True, '1.12')),
            # Test an incompatible Python.
            ((3, 6, 4), None, (False, None)),
            # Test an incompatible Python with ignore_requires_python=True.
            ((3, 6, 4), True, (True, '1.12')),
        ],
    )
    def test_evaluate_link(
        self, py_version_info, ignore_requires_python, expected,
    ):
        target_python = TargetPython(py_version_info=py_version_info)
        evaluator = CandidateEvaluator(
            target_python=target_python,
            ignore_requires_python=ignore_requires_python,
        )
        link = Link(
            'https://example.com/#egg=twine-1.12',
            requires_python='== 3.6.5',
        )
        search = Search(
            supplied='twine', canonical='twine', formats=['source'],
        )
        actual = evaluator.evaluate_link(link, search=search)
        assert actual == expected

    def test_evaluate_link__incompatible_wheel(self):
        """
        Test an incompatible wheel.
        """
        target_python = TargetPython(py_version_info=(3, 6, 4))
        # Set the valid tags to an empty list to make sure nothing matches.
        target_python._valid_tags = []
        evaluator = CandidateEvaluator(target_python=target_python)
        link = Link('https://example.com/sample-1.0-py2.py3-none-any.whl')
        search = Search(
            supplied='sample', canonical='sample', formats=['binary'],
        )
        actual = evaluator.evaluate_link(link, search=search)
        expected = (
            False, "none of the wheel's tags match: py2-none-any, py3-none-any"
        )
        assert actual == expected


class TestPackageFinder:

    def test_create__target_python(self):
        """
        Test that target_python is passed to CandidateEvaluator as is.
        """
        target_python = TargetPython(py_version_info=(3, 7, 3))
        finder = PackageFinder.create(
            [], [], target_python=target_python, session=object(),
        )

        evaluator = finder.candidate_evaluator
        actual_target_python = evaluator._target_python
        assert actual_target_python is target_python
        assert actual_target_python.py_version_info == (3, 7, 3)


def test_sort_locations_file_expand_dir(data):
    """
    Test that a file:// dir gets listdir run with expand_dir
    """
    finder = PackageFinder.create([data.find_links], [], session=PipSession())
    files, urls = finder._sort_locations([data.find_links], expand_dir=True)
    assert files and not urls, (
        "files and not urls should have been found at find-links url: %s" %
        data.find_links
    )


def test_sort_locations_file_not_find_link(data):
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir
    run
    """
    finder = PackageFinder.create([], [], session=PipSession())
    files, urls = finder._sort_locations([data.index_url("empty_with_pkg")])
    assert urls and not files, "urls, but not files should have been found"


def test_sort_locations_non_existing_path():
    """
    Test that a non-existing path is ignored.
    """
    finder = PackageFinder.create([], [], session=PipSession())
    files, urls = finder._sort_locations(
        [os.path.join('this', 'doesnt', 'exist')])
    assert not urls and not files, "nothing should have been found"


class TestLink(object):

    def test_splitext(self):
        assert ('wheel', '.whl') == Link('http://yo/wheel.whl').splitext()

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("http://yo/wheel.whl", "wheel.whl"),
            ("http://yo/wheel", "wheel"),
            (
                "http://yo/myproject-1.0%2Bfoobar.0-py2.py3-none-any.whl",
                "myproject-1.0+foobar.0-py2.py3-none-any.whl",
            ),
        ],
    )
    def test_filename(self, url, expected):
        assert Link(url).filename == expected

    def test_no_ext(self):
        assert '' == Link('http://yo/wheel').ext

    def test_ext(self):
        assert '.whl' == Link('http://yo/wheel.whl').ext

    def test_ext_fragment(self):
        assert '.whl' == Link('http://yo/wheel.whl#frag').ext

    def test_ext_query(self):
        assert '.whl' == Link('http://yo/wheel.whl?a=b').ext

    def test_is_wheel(self):
        assert Link('http://yo/wheel.whl').is_wheel

    def test_is_wheel_false(self):
        assert not Link('http://yo/not_a_wheel').is_wheel

    def test_fragments(self):
        url = 'git+https://example.com/package#egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#egg=eggname&subdirectory=subdir'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#subdirectory=subdir&egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment


@pytest.mark.parametrize(
    ("html", "url", "expected"),
    [
        (b"<html></html>", "https://example.com/", "https://example.com/"),
        (
            b"<html><head>"
            b"<base href=\"https://foo.example.com/\">"
            b"</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
        (
            b"<html><head>"
            b"<base><base href=\"https://foo.example.com/\">"
            b"</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
    ],
)
def test_determine_base_url(html, url, expected):
    document = html5lib.parse(
        html, transport_encoding=None, namespaceHTMLElements=False,
    )
    assert _determine_base_url(document, url) == expected


class MockLogger(object):
    def __init__(self):
        self.called = False

    def warning(self, *args, **kwargs):
        self.called = True


@pytest.mark.parametrize(
    ("location", "trusted", "expected"),
    [
        ("http://pypi.org/something", [], True),
        ("https://pypi.org/something", [], False),
        ("git+http://pypi.org/something", [], True),
        ("git+https://pypi.org/something", [], False),
        ("git+ssh://git@pypi.org/something", [], False),
        ("http://localhost", [], False),
        ("http://127.0.0.1", [], False),
        ("http://example.com/something/", [], True),
        ("http://example.com/something/", ["example.com"], False),
        ("http://eXample.com/something/", ["example.cOm"], False),
    ],
)
def test_secure_origin(location, trusted, expected):
    finder = PackageFinder.create([], [], session=[], trusted_hosts=trusted)
    logger = MockLogger()
    finder._validate_secure_origin(logger, location)
    assert logger.called == expected


def test_get_formatted_locations_basic_auth():
    """
    Test that basic authentication credentials defined in URL
    is not included in formatted output.
    """
    index_urls = [
        'https://pypi.org/simple',
        'https://repo-user:repo-pass@repo.domain.com',
    ]
    find_links = [
        'https://links-user:links-pass@page.domain.com'
    ]
    finder = PackageFinder.create(find_links, index_urls, session=[])

    result = finder.get_formatted_locations()
    assert 'repo-user:****@repo.domain.com' in result
    assert 'repo-pass' not in result
    assert 'links-user:****@page.domain.com' in result
    assert 'links-pass' not in result


@pytest.mark.parametrize(
    ("egg_info", "canonical_name", "expected"),
    [
        # Trivial.
        ("pip-18.0", "pip", 3),
        ("zope-interface-4.5.0", "zope-interface", 14),

        # Canonicalized name match non-canonicalized egg info. (pypa/pip#5870)
        ("Jinja2-2.10", "jinja2", 6),
        ("zope.interface-4.5.0", "zope-interface", 14),
        ("zope_interface-4.5.0", "zope-interface", 14),

        # Should be smart enough to parse ambiguous names from the provided
        # package name.
        ("foo-2-2", "foo", 3),
        ("foo-2-2", "foo-2", 5),

        # Should be able to detect collapsed characters in the egg info.
        ("foo--bar-1.0", "foo-bar", 8),
        ("foo-_bar-1.0", "foo-bar", 8),

        # The package name must not ends with a dash (PEP 508), so the first
        # dash would be the separator, not the second.
        ("zope.interface--4.5.0", "zope-interface", 14),
        ("zope.interface--", "zope-interface", 14),

        # The version part is missing, but the split function does not care.
        ("zope.interface-", "zope-interface", 14),
    ],
)
def test_find_name_version_sep(egg_info, canonical_name, expected):
    index = _find_name_version_sep(egg_info, canonical_name)
    assert index == expected


@pytest.mark.parametrize(
    ("egg_info", "canonical_name"),
    [
        # A dash must follow the package name.
        ("zope.interface4.5.0", "zope-interface"),
        ("zope.interface.4.5.0", "zope-interface"),
        ("zope.interface.-4.5.0", "zope-interface"),
        ("zope.interface", "zope-interface"),
    ],
)
def test_find_name_version_sep_failure(egg_info, canonical_name):
    with pytest.raises(ValueError) as ctx:
        _find_name_version_sep(egg_info, canonical_name)
    message = "{} does not match {}".format(egg_info, canonical_name)
    assert str(ctx.value) == message


@pytest.mark.parametrize(
    ("egg_info", "canonical_name", "expected"),
    [
        # Trivial.
        ("pip-18.0", "pip", "18.0"),
        ("zope-interface-4.5.0", "zope-interface", "4.5.0"),

        # Canonicalized name match non-canonicalized egg info. (pypa/pip#5870)
        ("Jinja2-2.10", "jinja2", "2.10"),
        ("zope.interface-4.5.0", "zope-interface", "4.5.0"),
        ("zope_interface-4.5.0", "zope-interface", "4.5.0"),

        # Should be smart enough to parse ambiguous names from the provided
        # package name.
        ("foo-2-2", "foo", "2-2"),
        ("foo-2-2", "foo-2", "2"),
        ("zope.interface--4.5.0", "zope-interface", "-4.5.0"),
        ("zope.interface--", "zope-interface", "-"),

        # Should be able to detect collapsed characters in the egg info.
        ("foo--bar-1.0", "foo-bar", "1.0"),
        ("foo-_bar-1.0", "foo-bar", "1.0"),

        # Invalid.
        ("the-package-name-8.19", "does-not-match", None),
        ("zope.interface.-4.5.0", "zope.interface", None),
        ("zope.interface-", "zope-interface", None),
        ("zope.interface4.5.0", "zope-interface", None),
        ("zope.interface.4.5.0", "zope-interface", None),
        ("zope.interface.-4.5.0", "zope-interface", None),
        ("zope.interface", "zope-interface", None),
    ],
)
def test_egg_info_matches(egg_info, canonical_name, expected):
    version = _egg_info_matches(egg_info, canonical_name)
    assert version == expected


def test_request_http_error(caplog):
    caplog.set_level(logging.DEBUG)
    link = Link('http://localhost')
    session = Mock(PipSession)
    session.get.return_value = resp = Mock()
    resp.raise_for_status.side_effect = requests.HTTPError('Http error')
    assert _get_html_page(link, session=session) is None
    assert (
        'Could not fetch URL http://localhost: Http error - skipping'
        in caplog.text
    )


def test_request_retries(caplog):
    caplog.set_level(logging.DEBUG)
    link = Link('http://localhost')
    session = Mock(PipSession)
    session.get.side_effect = requests.exceptions.RetryError('Retry error')
    assert _get_html_page(link, session=session) is None
    assert (
        'Could not fetch URL http://localhost: Retry error - skipping'
        in caplog.text
    )


@pytest.mark.parametrize(
    ("url", "clean_url"),
    [
        # URL with hostname and port. Port separator should not be quoted.
        ("https://localhost.localdomain:8181/path/with space/",
         "https://localhost.localdomain:8181/path/with%20space/"),
        # URL that is already properly quoted. The quoting `%`
        # characters should not be quoted again.
        ("https://localhost.localdomain:8181/path/with%20quoted%20space/",
         "https://localhost.localdomain:8181/path/with%20quoted%20space/"),
        # URL with IPv4 address and port.
        ("https://127.0.0.1:8181/path/with space/",
         "https://127.0.0.1:8181/path/with%20space/"),
        # URL with IPv6 address and port. The `[]` brackets around the
        # IPv6 address should not be quoted.
        ("https://[fd00:0:0:236::100]:8181/path/with space/",
         "https://[fd00:0:0:236::100]:8181/path/with%20space/"),
        # URL with query. The leading `?` should not be quoted.
        ("https://localhost.localdomain:8181/path/with/query?request=test",
         "https://localhost.localdomain:8181/path/with/query?request=test"),
        # URL with colon in the path portion.
        ("https://localhost.localdomain:8181/path:/with:/colon",
         "https://localhost.localdomain:8181/path%3A/with%3A/colon"),
        # URL with something that looks like a drive letter, but is
        # not. The `:` should be quoted.
        ("https://localhost.localdomain/T:/path/",
         "https://localhost.localdomain/T%3A/path/"),
        # VCS URL containing revision string.
        ("git+ssh://example.com/path to/repo.git@1.0#egg=my-package-1.0",
         "git+ssh://example.com/path%20to/repo.git@1.0#egg=my-package-1.0")
    ]
)
def test_clean_link(url, clean_url):
    assert(_clean_link(url) == clean_url)


@pytest.mark.parametrize(
    ("url", "clean_url"),
    [
        # URL with Windows drive letter. The `:` after the drive
        # letter should not be quoted. The trailing `/` should be
        # removed.
        ("file:///T:/path/with spaces/",
         "file:///T:/path/with%20spaces")
    ]
)
@pytest.mark.skipif("sys.platform != 'win32'")
def test_clean_link_windows(url, clean_url):
    assert(_clean_link(url) == clean_url)


@pytest.mark.parametrize(
    ("url", "clean_url"),
    [
        # URL with Windows drive letter, running on non-windows
        # platform. The `:` after the drive should be quoted.
        ("file:///T:/path/with spaces/",
         "file:///T%3A/path/with%20spaces/")
    ]
)
@pytest.mark.skipif("sys.platform == 'win32'")
def test_clean_link_non_windows(url, clean_url):
    assert(_clean_link(url) == clean_url)
