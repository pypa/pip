import logging
import os.path

import pytest
from mock import Mock
from pip._vendor import html5lib, requests
from pip._vendor.packaging.specifiers import SpecifierSet

from pip._internal.download import PipSession
from pip._internal.index import (
    CandidateEvaluator,
    CandidatePreferences,
    FormatControl,
    HTMLPage,
    Link,
    LinkEvaluator,
    PackageFinder,
    _check_link_requires_python,
    _clean_link,
    _determine_base_url,
    _extract_version_from_fragment,
    _find_name_version_sep,
    _get_html_page,
    filter_unallowed_hashes,
)
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.pep425tags import get_supported
from pip._internal.utils.hashes import Hashes
from tests.lib import CURRENT_PY_VERSION_INFO, make_test_finder


def make_mock_candidate(version, yanked_reason=None, hex_digest=None):
    url = 'https://example.com/pkg-{}.tar.gz'.format(version)
    if hex_digest is not None:
        assert len(hex_digest) == 64
        url += '#sha256={}'.format(hex_digest)

    link = Link(url, yanked_reason=yanked_reason)
    candidate = InstallationCandidate('mypackage', version, link)

    return candidate


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


class TestLinkEvaluator:

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
        evaluator = LinkEvaluator(
            project_name='twine',
            canonical_name='twine',
            formats={'source'},
            target_python=target_python,
            allow_yanked=True,
            ignore_requires_python=ignore_requires_python,
        )
        link = Link(
            'https://example.com/#egg=twine-1.12',
            requires_python='== 3.6.5',
        )
        actual = evaluator.evaluate_link(link)
        assert actual == expected

    @pytest.mark.parametrize('yanked_reason, allow_yanked, expected', [
        (None, True, (True, '1.12')),
        (None, False, (True, '1.12')),
        ('', True, (True, '1.12')),
        ('', False, (False, 'yanked for reason: <none given>')),
        ('bad metadata', True, (True, '1.12')),
        ('bad metadata', False,
         (False, 'yanked for reason: bad metadata')),
        # Test a unicode string with a non-ascii character.
        (u'curly quote: \u2018', True, (True, '1.12')),
        (u'curly quote: \u2018', False,
         (False, u'yanked for reason: curly quote: \u2018')),
    ])
    def test_evaluate_link__allow_yanked(
        self, yanked_reason, allow_yanked, expected,
    ):
        target_python = TargetPython(py_version_info=(3, 6, 4))
        evaluator = LinkEvaluator(
            project_name='twine',
            canonical_name='twine',
            formats={'source'},
            target_python=target_python,
            allow_yanked=allow_yanked,
        )
        link = Link(
            'https://example.com/#egg=twine-1.12',
            yanked_reason=yanked_reason,
        )
        actual = evaluator.evaluate_link(link)
        assert actual == expected

    def test_evaluate_link__incompatible_wheel(self):
        """
        Test an incompatible wheel.
        """
        target_python = TargetPython(py_version_info=(3, 6, 4))
        # Set the valid tags to an empty list to make sure nothing matches.
        target_python._valid_tags = []
        evaluator = LinkEvaluator(
            project_name='sample',
            canonical_name='sample',
            formats={'binary'},
            target_python=target_python,
            allow_yanked=True,
        )
        link = Link('https://example.com/sample-1.0-py2.py3-none-any.whl')
        actual = evaluator.evaluate_link(link)
        expected = (
            False, "none of the wheel's tags match: py2-none-any, py3-none-any"
        )
        assert actual == expected


@pytest.mark.parametrize('hex_digest, expected_versions', [
    (None, ['1.0', '1.1', '1.2']),
    (64 * 'a', ['1.0', '1.1']),
    (64 * 'b', ['1.0', '1.2']),
    (64 * 'c', ['1.0', '1.1', '1.2']),
])
def test_filter_unallowed_hashes(hex_digest, expected_versions):
    candidates = [
        make_mock_candidate('1.0'),
        make_mock_candidate('1.1', hex_digest=(64 * 'a')),
        make_mock_candidate('1.2', hex_digest=(64 * 'b')),
    ]
    hashes_data = {
        'sha256': [hex_digest],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates, hashes=hashes, project_name='my-project',
    )

    actual_versions = [str(candidate.version) for candidate in actual]
    assert actual_versions == expected_versions
    # Check that the return value is always different from the given value.
    assert actual is not candidates


def test_filter_unallowed_hashes__no_hashes(caplog):
    caplog.set_level(logging.DEBUG)

    candidates = [
        make_mock_candidate('1.0'),
        make_mock_candidate('1.1'),
    ]
    actual = filter_unallowed_hashes(
        candidates, hashes=Hashes(), project_name='my-project',
    )

    # Check that the return value is a copy.
    assert actual == candidates
    assert actual is not candidates

    expected_message = (
        "Given no hashes to check 2 links for project 'my-project': "
        "discarding no candidates"
    )
    check_caplog(caplog, 'DEBUG', expected_message)


def test_filter_unallowed_hashes__log_message_with_match(caplog):
    caplog.set_level(logging.DEBUG)

    # Test 1 match, 2 non-matches, 3 no hashes so all 3 values will be
    # different.
    candidates = [
        make_mock_candidate('1.0'),
        make_mock_candidate('1.1',),
        make_mock_candidate('1.2',),
        make_mock_candidate('1.3', hex_digest=(64 * 'a')),
        make_mock_candidate('1.4', hex_digest=(64 * 'b')),
        make_mock_candidate('1.5', hex_digest=(64 * 'c')),
    ]
    hashes_data = {
        'sha256': [64 * 'a', 64 * 'd'],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates, hashes=hashes, project_name='my-project',
    )
    assert len(actual) == 4

    expected_message = (
        "Checked 6 links for project 'my-project' against 2 hashes "
        "(1 matches, 3 no digest): discarding 2 non-matches:\n"
        "  https://example.com/pkg-1.4.tar.gz#sha256="
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
        "  https://example.com/pkg-1.5.tar.gz#sha256="
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    )
    check_caplog(caplog, 'DEBUG', expected_message)


def test_filter_unallowed_hashes__log_message_with_no_match(caplog):
    caplog.set_level(logging.DEBUG)

    candidates = [
        make_mock_candidate('1.0'),
        make_mock_candidate('1.1', hex_digest=(64 * 'b')),
        make_mock_candidate('1.2', hex_digest=(64 * 'c')),
    ]
    hashes_data = {
        'sha256': [64 * 'a', 64 * 'd'],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates, hashes=hashes, project_name='my-project',
    )
    assert len(actual) == 3

    expected_message = (
        "Checked 3 links for project 'my-project' against 2 hashes "
        "(0 matches, 1 no digest): discarding no candidates"
    )
    check_caplog(caplog, 'DEBUG', expected_message)


class TestCandidateEvaluator:

    @pytest.mark.parametrize('allow_all_prereleases, prefer_binary', [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ])
    def test_create(self, allow_all_prereleases, prefer_binary):
        target_python = TargetPython()
        target_python._valid_tags = [('py36', 'none', 'any')]
        specifier = SpecifierSet()
        evaluator = CandidateEvaluator.create(
            project_name='my-project',
            target_python=target_python,
            allow_all_prereleases=allow_all_prereleases,
            prefer_binary=prefer_binary,
            specifier=specifier,
        )
        assert evaluator._allow_all_prereleases == allow_all_prereleases
        assert evaluator._prefer_binary == prefer_binary
        assert evaluator._specifier is specifier
        assert evaluator._supported_tags == [('py36', 'none', 'any')]

    def test_create__target_python_none(self):
        """
        Test passing target_python=None.
        """
        evaluator = CandidateEvaluator.create('my-project')
        expected_tags = get_supported()
        assert evaluator._supported_tags == expected_tags

    def test_create__specifier_none(self):
        """
        Test passing specifier=None.
        """
        evaluator = CandidateEvaluator.create('my-project')
        expected_specifier = SpecifierSet()
        assert evaluator._specifier == expected_specifier

    def test_get_applicable_candidates(self):
        specifier = SpecifierSet('<= 1.11')
        versions = ['1.10', '1.11', '1.12']
        candidates = [
            make_mock_candidate(version) for version in versions
        ]
        evaluator = CandidateEvaluator.create(
            'my-project',
            specifier=specifier,
        )
        actual = evaluator.get_applicable_candidates(candidates)
        expected_applicable = candidates[:2]
        assert [str(c.version) for c in expected_applicable] == [
            '1.10',
            '1.11',
        ]
        assert actual == expected_applicable

    @pytest.mark.parametrize('specifier, expected_versions', [
        # Test no version constraint.
        (SpecifierSet(), ['1.0', '1.2']),
        # Test a version constraint that excludes the candidate whose
        # hash matches.  Then the non-allowed hash is a candidate.
        (SpecifierSet('<= 1.1'), ['1.0', '1.1']),
    ])
    def test_get_applicable_candidates__hashes(
        self, specifier, expected_versions,
    ):
        """
        Test a non-None hashes value.
        """
        candidates = [
            make_mock_candidate('1.0'),
            make_mock_candidate('1.1', hex_digest=(64 * 'a')),
            make_mock_candidate('1.2', hex_digest=(64 * 'b')),
        ]
        hashes_data = {
            'sha256': [64 * 'b'],
        }
        hashes = Hashes(hashes_data)
        evaluator = CandidateEvaluator.create(
            'my-project',
            specifier=specifier,
            hashes=hashes,
        )
        actual = evaluator.get_applicable_candidates(candidates)
        actual_versions = [str(c.version) for c in actual]
        assert actual_versions == expected_versions

    def test_make_found_candidates(self):
        specifier = SpecifierSet('<= 1.11')
        versions = ['1.10', '1.11', '1.12']
        candidates = [
            make_mock_candidate(version) for version in versions
        ]
        evaluator = CandidateEvaluator.create(
            'my-project',
            specifier=specifier,
        )
        found_candidates = evaluator.make_found_candidates(candidates)

        assert found_candidates._candidates == candidates
        assert found_candidates._evaluator is evaluator
        expected_applicable = candidates[:2]
        assert [str(c.version) for c in expected_applicable] == [
            '1.10',
            '1.11',
        ]
        assert found_candidates._applicable_candidates == expected_applicable

    @pytest.mark.parametrize('hex_digest, expected', [
        # Test a link with no hash.
        (None, 0),
        # Test a link with an allowed hash.
        (64 * 'a', 1),
        # Test a link with a hash that isn't allowed.
        (64 * 'b', 0),
    ])
    def test_sort_key__hash(self, hex_digest, expected):
        """
        Test the effect of the link's hash on _sort_key()'s return value.
        """
        candidate = make_mock_candidate('1.0', hex_digest=hex_digest)
        hashes_data = {
            'sha256': [64 * 'a'],
        }
        hashes = Hashes(hashes_data)
        evaluator = CandidateEvaluator.create('my-project', hashes=hashes)
        sort_value = evaluator._sort_key(candidate)
        # The hash is reflected in the first element of the tuple.
        actual = sort_value[0]
        assert actual == expected

    @pytest.mark.parametrize('yanked_reason, expected', [
        # Test a non-yanked file.
        (None, 0),
        # Test a yanked file (has a lower value than non-yanked).
        ('bad metadata', -1),
    ])
    def test_sort_key__is_yanked(self, yanked_reason, expected):
        """
        Test the effect of is_yanked on _sort_key()'s return value.
        """
        candidate = make_mock_candidate('1.0', yanked_reason=yanked_reason)
        evaluator = CandidateEvaluator.create('my-project')
        sort_value = evaluator._sort_key(candidate)
        # Yanked / non-yanked is reflected in the second element of the tuple.
        actual = sort_value[1]
        assert actual == expected

    def test_get_best_candidate__no_candidates(self):
        """
        Test passing an empty list.
        """
        evaluator = CandidateEvaluator.create('my-project')
        actual = evaluator.get_best_candidate([])
        assert actual is None

    def test_get_best_candidate__all_yanked(self, caplog):
        """
        Test all candidates yanked.
        """
        candidates = [
            make_mock_candidate('1.0', yanked_reason='bad metadata #1'),
            # Put the best candidate in the middle, to test sorting.
            make_mock_candidate('3.0', yanked_reason='bad metadata #3'),
            make_mock_candidate('2.0', yanked_reason='bad metadata #2'),
        ]
        expected_best = candidates[1]
        evaluator = CandidateEvaluator.create('my-project')
        actual = evaluator.get_best_candidate(candidates)
        assert actual is expected_best
        assert str(actual.version) == '3.0'

        # Check the log messages.
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == 'WARNING'
        assert record.message == (
            'The candidate selected for download or install is a yanked '
            "version: 'mypackage' candidate "
            '(version 3.0 at https://example.com/pkg-3.0.tar.gz)\n'
            'Reason for being yanked: bad metadata #3'
        )

    @pytest.mark.parametrize('yanked_reason, expected_reason', [
        # Test no reason given.
        ('', '<none given>'),
        # Test a unicode string with a non-ascii character.
        (u'curly quote: \u2018', u'curly quote: \u2018'),
    ])
    def test_get_best_candidate__yanked_reason(
        self, caplog, yanked_reason, expected_reason,
    ):
        """
        Test the log message with various reason strings.
        """
        candidates = [
            make_mock_candidate('1.0', yanked_reason=yanked_reason),
        ]
        evaluator = CandidateEvaluator.create('my-project')
        actual = evaluator.get_best_candidate(candidates)
        assert str(actual.version) == '1.0'

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == 'WARNING'
        expected_message = (
            'The candidate selected for download or install is a yanked '
            "version: 'mypackage' candidate "
            '(version 1.0 at https://example.com/pkg-1.0.tar.gz)\n'
            'Reason for being yanked: '
        ) + expected_reason
        assert record.message == expected_message

    def test_get_best_candidate__best_yanked_but_not_all(self, caplog):
        """
        Test the best candidates being yanked, but not all.
        """
        candidates = [
            make_mock_candidate('4.0', yanked_reason='bad metadata #4'),
            # Put the best candidate in the middle, to test sorting.
            make_mock_candidate('2.0'),
            make_mock_candidate('3.0', yanked_reason='bad metadata #3'),
            make_mock_candidate('1.0'),
        ]
        expected_best = candidates[1]
        evaluator = CandidateEvaluator.create('my-project')
        actual = evaluator.get_best_candidate(candidates)
        assert actual is expected_best
        assert str(actual.version) == '2.0'

        # Check the log messages.
        assert len(caplog.records) == 0


class TestPackageFinder:

    @pytest.mark.parametrize('allow_all_prereleases, prefer_binary', [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ])
    def test_create__candidate_prefs(
        self, allow_all_prereleases, prefer_binary,
    ):
        """
        Test that the _candidate_prefs attribute is set correctly.
        """
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            allow_all_prereleases=allow_all_prereleases,
            prefer_binary=prefer_binary,
        )
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=selection_prefs,
            session=PipSession(),
        )
        candidate_prefs = finder._candidate_prefs
        assert candidate_prefs.allow_all_prereleases == allow_all_prereleases
        assert candidate_prefs.prefer_binary == prefer_binary

    def test_create__target_python(self):
        """
        Test that the _target_python attribute is set correctly.
        """
        target_python = TargetPython(py_version_info=(3, 7, 3))
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=SelectionPreferences(allow_yanked=True),
            session=PipSession(),
            target_python=target_python,
        )
        actual_target_python = finder._target_python
        # The target_python attribute should be set as is.
        assert actual_target_python is target_python
        # Check that the attributes weren't reset.
        assert actual_target_python.py_version_info == (3, 7, 3)

    def test_create__target_python_none(self):
        """
        Test passing target_python=None.
        """
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=SelectionPreferences(allow_yanked=True),
            session=PipSession(),
            target_python=None,
        )
        # Spot-check the default TargetPython object.
        actual_target_python = finder._target_python
        assert actual_target_python._given_py_version_info is None
        assert actual_target_python.py_version_info == CURRENT_PY_VERSION_INFO

    @pytest.mark.parametrize('allow_yanked', [False, True])
    def test_create__allow_yanked(self, allow_yanked):
        """
        Test that the _allow_yanked attribute is set correctly.
        """
        selection_prefs = SelectionPreferences(allow_yanked=allow_yanked)
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=selection_prefs,
            session=PipSession(),
        )
        assert finder._allow_yanked == allow_yanked

    @pytest.mark.parametrize('ignore_requires_python', [False, True])
    def test_create__ignore_requires_python(self, ignore_requires_python):
        """
        Test that the _ignore_requires_python attribute is set correctly.
        """
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            ignore_requires_python=ignore_requires_python,
        )
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=selection_prefs,
            session=PipSession(),
        )
        assert finder._ignore_requires_python == ignore_requires_python

    def test_create__format_control(self):
        """
        Test that the format_control attribute is set correctly.
        """
        format_control = FormatControl(set(), {':all:'})
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            format_control=format_control,
        )
        finder = PackageFinder.create(
            search_scope=SearchScope([], []),
            selection_prefs=selection_prefs,
            session=PipSession(),
        )
        actual_format_control = finder.format_control
        assert actual_format_control is format_control
        # Check that the attributes weren't reset.
        assert actual_format_control.only_binary == {':all:'}

    def test_add_trusted_host(self):
        # Leave a gap to test how the ordering is affected.
        trusted_hosts = ['host1', 'host3']
        session = PipSession(insecure_hosts=trusted_hosts)
        finder = make_test_finder(
            session=session,
            trusted_hosts=trusted_hosts,
        )
        insecure_adapter = session._insecure_adapter
        prefix2 = 'https://host2/'
        prefix3 = 'https://host3/'

        # Confirm some initial conditions as a baseline.
        assert finder.trusted_hosts == ['host1', 'host3']
        assert session.adapters[prefix3] is insecure_adapter
        assert prefix2 not in session.adapters

        # Test adding a new host.
        finder.add_trusted_host('host2')
        assert finder.trusted_hosts == ['host1', 'host3', 'host2']
        # Check that prefix3 is still present.
        assert session.adapters[prefix3] is insecure_adapter
        assert session.adapters[prefix2] is insecure_adapter

        # Test that adding the same host doesn't create a duplicate.
        finder.add_trusted_host('host3')
        assert finder.trusted_hosts == ['host1', 'host3', 'host2'], (
            'actual: {}'.format(finder.trusted_hosts)
        )

    def test_add_trusted_host__logging(self, caplog):
        """
        Test logging when add_trusted_host() is called.
        """
        trusted_hosts = ['host1']
        session = PipSession(insecure_hosts=trusted_hosts)
        finder = make_test_finder(
            session=session,
            trusted_hosts=trusted_hosts,
        )
        with caplog.at_level(logging.INFO):
            # Test adding an existing host.
            finder.add_trusted_host('host1', source='somewhere')
            finder.add_trusted_host('host2')
            # Test calling add_trusted_host() on the same host twice.
            finder.add_trusted_host('host2')

        actual = [(r.levelname, r.message) for r in caplog.records]
        expected = [
            ('INFO', "adding trusted host: 'host1' (from somewhere)"),
            ('INFO', "adding trusted host: 'host2'"),
            ('INFO', "adding trusted host: 'host2'"),
        ]
        assert actual == expected

    def test_iter_secure_origins(self):
        trusted_hosts = ['host1', 'host2']
        finder = make_test_finder(trusted_hosts=trusted_hosts)

        actual = list(finder.iter_secure_origins())
        assert len(actual) == 8
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ('https', '*', '*')
        assert actual[-2:] == [
            ('*', 'host1', '*'),
            ('*', 'host2', '*'),
        ]

    def test_iter_secure_origins__none_trusted_hosts(self):
        """
        Test iter_secure_origins() after passing trusted_hosts=None.
        """
        # Use PackageFinder.create() rather than make_test_finder()
        # to make sure we're really passing trusted_hosts=None.
        search_scope = SearchScope([], [])
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
        )
        finder = PackageFinder.create(
            search_scope=search_scope,
            selection_prefs=selection_prefs,
            trusted_hosts=None,
            session=object(),
        )

        actual = list(finder.iter_secure_origins())
        assert len(actual) == 6
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ('https', '*', '*')

    @pytest.mark.parametrize(
        'allow_yanked, ignore_requires_python, only_binary, expected_formats',
        [
            (False, False, {}, frozenset({'binary', 'source'})),
            # Test allow_yanked=True.
            (True, False, {}, frozenset({'binary', 'source'})),
            # Test ignore_requires_python=True.
            (False, True, {}, frozenset({'binary', 'source'})),
            # Test a non-trivial only_binary.
            (False, False, {'twine'}, frozenset({'binary'})),
        ]
    )
    def test_make_link_evaluator(
        self, allow_yanked, ignore_requires_python, only_binary,
        expected_formats,
    ):
        # Create a test TargetPython that we can check for.
        target_python = TargetPython(py_version_info=(3, 7))
        format_control = FormatControl(set(), only_binary)
        finder = PackageFinder(
            search_scope=SearchScope([], []),
            session=PipSession(),
            target_python=target_python,
            allow_yanked=allow_yanked,
            format_control=format_control,
            ignore_requires_python=ignore_requires_python,
        )

        # Pass a project_name that will be different from canonical_name.
        link_evaluator = finder.make_link_evaluator('Twine')

        assert link_evaluator.project_name == 'Twine'
        assert link_evaluator._canonical_name == 'twine'
        assert link_evaluator._allow_yanked == allow_yanked
        assert link_evaluator._ignore_requires_python == ignore_requires_python
        assert link_evaluator._formats == expected_formats

        # Test the _target_python attribute.
        actual_target_python = link_evaluator._target_python
        # The target_python attribute should be set as is.
        assert actual_target_python is target_python
        # For good measure, check that the attributes weren't reset.
        assert actual_target_python._given_py_version_info == (3, 7)
        assert actual_target_python.py_version_info == (3, 7, 0)

    @pytest.mark.parametrize('allow_all_prereleases, prefer_binary', [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ])
    def test_make_candidate_evaluator(
        self, allow_all_prereleases, prefer_binary,
    ):
        target_python = TargetPython()
        target_python._valid_tags = [('py36', 'none', 'any')]
        candidate_prefs = CandidatePreferences(
            prefer_binary=prefer_binary,
            allow_all_prereleases=allow_all_prereleases,
        )
        finder = PackageFinder(
            search_scope=SearchScope([], []),
            session=PipSession(),
            target_python=target_python,
            allow_yanked=True,
            candidate_prefs=candidate_prefs,
        )

        specifier = SpecifierSet()
        # Pass hashes to check that _hashes is set.
        hashes = Hashes({'sha256': [64 * 'a']})
        evaluator = finder.make_candidate_evaluator(
            'my-project',
            specifier=specifier,
            hashes=hashes,
        )
        assert evaluator._allow_all_prereleases == allow_all_prereleases
        assert evaluator._hashes == hashes
        assert evaluator._prefer_binary == prefer_binary
        assert evaluator._project_name == 'my-project'
        assert evaluator._specifier is specifier
        assert evaluator._supported_tags == [('py36', 'none', 'any')]


def test_sort_locations_file_expand_dir(data):
    """
    Test that a file:// dir gets listdir run with expand_dir
    """
    finder = make_test_finder(find_links=[data.find_links])
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
    finder = make_test_finder()
    files, urls = finder._sort_locations([data.index_url("empty_with_pkg")])
    assert urls and not files, "urls, but not files should have been found"


def test_sort_locations_non_existing_path():
    """
    Test that a non-existing path is ignored.
    """
    finder = make_test_finder()
    files, urls = finder._sort_locations(
        [os.path.join('this', 'doesnt', 'exist')])
    assert not urls and not files, "nothing should have been found"


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
    finder = make_test_finder(trusted_hosts=trusted)
    logger = MockLogger()
    finder._validate_secure_origin(logger, location)
    assert logger.called == expected


@pytest.mark.parametrize(
    ("fragment", "canonical_name", "expected"),
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
def test_find_name_version_sep(fragment, canonical_name, expected):
    index = _find_name_version_sep(fragment, canonical_name)
    assert index == expected


@pytest.mark.parametrize(
    ("fragment", "canonical_name"),
    [
        # A dash must follow the package name.
        ("zope.interface4.5.0", "zope-interface"),
        ("zope.interface.4.5.0", "zope-interface"),
        ("zope.interface.-4.5.0", "zope-interface"),
        ("zope.interface", "zope-interface"),
    ],
)
def test_find_name_version_sep_failure(fragment, canonical_name):
    with pytest.raises(ValueError) as ctx:
        _find_name_version_sep(fragment, canonical_name)
    message = "{} does not match {}".format(fragment, canonical_name)
    assert str(ctx.value) == message


@pytest.mark.parametrize(
    ("fragment", "canonical_name", "expected"),
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
def test_extract_version_from_fragment(fragment, canonical_name, expected):
    version = _extract_version_from_fragment(fragment, canonical_name)
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


class TestHTMLPage:

    @pytest.mark.parametrize(
        ('anchor_html, expected'),
        [
            # Test not present.
            ('<a href="/pkg1-1.0.tar.gz"></a>', None),
            # Test present with no value.
            ('<a href="/pkg2-1.0.tar.gz" data-yanked></a>', ''),
            # Test the empty string.
            ('<a href="/pkg3-1.0.tar.gz" data-yanked=""></a>', ''),
            # Test a non-empty string.
            ('<a href="/pkg4-1.0.tar.gz" data-yanked="error"></a>', 'error'),
            # Test a value with an escaped character.
            ('<a href="/pkg4-1.0.tar.gz" data-yanked="version &lt 1"></a>',
                'version < 1'),
            # Test a yanked reason with a non-ascii character.
            (u'<a href="/pkg-1.0.tar.gz" data-yanked="curlyquote \u2018"></a>',
                u'curlyquote \u2018'),
        ]
    )
    def test_iter_links__yanked_reason(self, anchor_html, expected):
        html = (
            # Mark this as a unicode string for Python 2 since anchor_html
            # can contain non-ascii.
            u'<html><head><meta charset="utf-8"><head>'
            '<body>{}</body></html>'
        ).format(anchor_html)
        html_bytes = html.encode('utf-8')
        page = HTMLPage(html_bytes, url='https://example.com/simple/')
        links = list(page.iter_links())
        link, = links
        actual = link.yanked_reason
        assert actual == expected
