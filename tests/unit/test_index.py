import logging

import pytest
from pip._vendor.packaging.specifiers import SpecifierSet

from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import (
    CandidateEvaluator,
    CandidatePreferences,
    FormatControl,
    LinkEvaluator,
    PackageFinder,
    _check_link_requires_python,
    _extract_version_from_fragment,
    _find_name_version_sep,
    filter_unallowed_hashes,
)
from pip._internal.models.link import Link
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.network.session import PipSession
from pip._internal.utils.compatibility_tags import get_supported
from pip._internal.utils.hashes import Hashes
from tests.lib import CURRENT_PY_VERSION_INFO
from tests.lib.index import make_mock_candidate


@pytest.mark.parametrize(
    "requires_python, expected",
    [
        ("== 3.6.4", False),
        ("== 3.6.5", True),
        # Test an invalid Requires-Python value.
        ("invalid", True),
    ],
)
def test_check_link_requires_python(requires_python, expected):
    version_info = (3, 6, 5)
    link = Link("https://example.com", requires_python=requires_python)
    actual = _check_link_requires_python(link, version_info)
    assert actual == expected


def check_caplog(caplog, expected_level, expected_message):
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == expected_level
    assert record.message == expected_message


@pytest.mark.parametrize(
    "ignore_requires_python, expected",
    [
        (
            None,
            (
                False,
                "VERBOSE",
                "Link requires a different Python (3.6.5 not in: '== 3.6.4'): "
                "https://example.com",
            ),
        ),
        (
            True,
            (
                True,
                "DEBUG",
                "Ignoring failed Requires-Python check (3.6.5 not in: '== 3.6.4') "
                "for link: https://example.com",
            ),
        ),
    ],
)
def test_check_link_requires_python__incompatible_python(
    caplog,
    ignore_requires_python,
    expected,
):
    """
    Test an incompatible Python.
    """
    expected_return, expected_level, expected_message = expected
    link = Link("https://example.com", requires_python="== 3.6.4")
    caplog.set_level(logging.DEBUG)
    actual = _check_link_requires_python(
        link,
        version_info=(3, 6, 5),
        ignore_requires_python=ignore_requires_python,
    )
    assert actual == expected_return

    check_caplog(caplog, expected_level, expected_message)


def test_check_link_requires_python__invalid_requires(caplog):
    """
    Test the log message for an invalid Requires-Python.
    """
    link = Link("https://example.com", requires_python="invalid")
    caplog.set_level(logging.DEBUG)
    actual = _check_link_requires_python(link, version_info=(3, 6, 5))
    assert actual

    expected_message = (
        "Ignoring invalid Requires-Python ('invalid') for link: https://example.com"
    )
    check_caplog(caplog, "DEBUG", expected_message)


class TestLinkEvaluator:
    @pytest.mark.parametrize(
        "py_version_info,ignore_requires_python,expected",
        [
            ((3, 6, 5), None, (True, "1.12")),
            # Test an incompatible Python.
            ((3, 6, 4), None, (False, None)),
            # Test an incompatible Python with ignore_requires_python=True.
            ((3, 6, 4), True, (True, "1.12")),
        ],
    )
    def test_evaluate_link(
        self,
        py_version_info,
        ignore_requires_python,
        expected,
    ):
        target_python = TargetPython(py_version_info=py_version_info)
        evaluator = LinkEvaluator(
            project_name="twine",
            canonical_name="twine",
            formats={"source"},
            target_python=target_python,
            allow_yanked=True,
            ignore_requires_python=ignore_requires_python,
        )
        link = Link(
            "https://example.com/#egg=twine-1.12",
            requires_python="== 3.6.5",
        )
        actual = evaluator.evaluate_link(link)
        assert actual == expected

    @pytest.mark.parametrize(
        "yanked_reason, allow_yanked, expected",
        [
            (None, True, (True, "1.12")),
            (None, False, (True, "1.12")),
            ("", True, (True, "1.12")),
            ("", False, (False, "yanked for reason: <none given>")),
            ("bad metadata", True, (True, "1.12")),
            ("bad metadata", False, (False, "yanked for reason: bad metadata")),
            # Test a unicode string with a non-ascii character.
            ("curly quote: \u2018", True, (True, "1.12")),
            (
                "curly quote: \u2018",
                False,
                (False, "yanked for reason: curly quote: \u2018"),
            ),
        ],
    )
    def test_evaluate_link__allow_yanked(
        self,
        yanked_reason,
        allow_yanked,
        expected,
    ):
        target_python = TargetPython(py_version_info=(3, 6, 4))
        evaluator = LinkEvaluator(
            project_name="twine",
            canonical_name="twine",
            formats={"source"},
            target_python=target_python,
            allow_yanked=allow_yanked,
        )
        link = Link(
            "https://example.com/#egg=twine-1.12",
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
            project_name="sample",
            canonical_name="sample",
            formats={"binary"},
            target_python=target_python,
            allow_yanked=True,
        )
        link = Link("https://example.com/sample-1.0-py2.py3-none-any.whl")
        actual = evaluator.evaluate_link(link)
        expected = (
            False,
            "none of the wheel's tags (py2-none-any, py3-none-any) are compatible "
            "(run pip debug --verbose to show compatible tags)",
        )
        assert actual == expected


@pytest.mark.parametrize(
    "hex_digest, expected_versions",
    [
        (None, ["1.0", "1.1", "1.2"]),
        (64 * "a", ["1.0", "1.1"]),
        (64 * "b", ["1.0", "1.2"]),
        (64 * "c", ["1.0", "1.1", "1.2"]),
    ],
)
def test_filter_unallowed_hashes(hex_digest, expected_versions):
    candidates = [
        make_mock_candidate("1.0"),
        make_mock_candidate("1.1", hex_digest=(64 * "a")),
        make_mock_candidate("1.2", hex_digest=(64 * "b")),
    ]
    hashes_data = {
        "sha256": [hex_digest],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates,
        hashes=hashes,
        project_name="my-project",
    )

    actual_versions = [str(candidate.version) for candidate in actual]
    assert actual_versions == expected_versions
    # Check that the return value is always different from the given value.
    assert actual is not candidates


def test_filter_unallowed_hashes__no_hashes(caplog):
    caplog.set_level(logging.DEBUG)

    candidates = [
        make_mock_candidate("1.0"),
        make_mock_candidate("1.1"),
    ]
    actual = filter_unallowed_hashes(
        candidates,
        hashes=Hashes(),
        project_name="my-project",
    )

    # Check that the return value is a copy.
    assert actual == candidates
    assert actual is not candidates

    expected_message = (
        "Given no hashes to check 2 links for project 'my-project': "
        "discarding no candidates"
    )
    check_caplog(caplog, "DEBUG", expected_message)


def test_filter_unallowed_hashes__log_message_with_match(caplog):
    caplog.set_level(logging.DEBUG)

    # Test 1 match, 2 non-matches, 3 no hashes so all 3 values will be
    # different.
    candidates = [
        make_mock_candidate("1.0"),
        make_mock_candidate(
            "1.1",
        ),
        make_mock_candidate(
            "1.2",
        ),
        make_mock_candidate("1.3", hex_digest=(64 * "a")),
        make_mock_candidate("1.4", hex_digest=(64 * "b")),
        make_mock_candidate("1.5", hex_digest=(64 * "c")),
    ]
    hashes_data = {
        "sha256": [64 * "a", 64 * "d"],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates,
        hashes=hashes,
        project_name="my-project",
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
    check_caplog(caplog, "DEBUG", expected_message)


def test_filter_unallowed_hashes__log_message_with_no_match(caplog):
    caplog.set_level(logging.DEBUG)

    candidates = [
        make_mock_candidate("1.0"),
        make_mock_candidate("1.1", hex_digest=(64 * "b")),
        make_mock_candidate("1.2", hex_digest=(64 * "c")),
    ]
    hashes_data = {
        "sha256": [64 * "a", 64 * "d"],
    }
    hashes = Hashes(hashes_data)
    actual = filter_unallowed_hashes(
        candidates,
        hashes=hashes,
        project_name="my-project",
    )
    assert len(actual) == 3

    expected_message = (
        "Checked 3 links for project 'my-project' against 2 hashes "
        "(0 matches, 1 no digest): discarding no candidates"
    )
    check_caplog(caplog, "DEBUG", expected_message)


class TestCandidateEvaluator:
    @pytest.mark.parametrize(
        "allow_all_prereleases, prefer_binary",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_create(self, allow_all_prereleases, prefer_binary):
        target_python = TargetPython()
        target_python._valid_tags = [("py36", "none", "any")]
        specifier = SpecifierSet()
        evaluator = CandidateEvaluator.create(
            project_name="my-project",
            target_python=target_python,
            allow_all_prereleases=allow_all_prereleases,
            prefer_binary=prefer_binary,
            specifier=specifier,
        )
        assert evaluator._allow_all_prereleases == allow_all_prereleases
        assert evaluator._prefer_binary == prefer_binary
        assert evaluator._specifier is specifier
        assert evaluator._supported_tags == [("py36", "none", "any")]

    def test_create__target_python_none(self):
        """
        Test passing target_python=None.
        """
        evaluator = CandidateEvaluator.create("my-project")
        expected_tags = get_supported()
        assert evaluator._supported_tags == expected_tags

    def test_create__specifier_none(self):
        """
        Test passing specifier=None.
        """
        evaluator = CandidateEvaluator.create("my-project")
        expected_specifier = SpecifierSet()
        assert evaluator._specifier == expected_specifier

    def test_get_applicable_candidates(self):
        specifier = SpecifierSet("<= 1.11")
        versions = ["1.10", "1.11", "1.12"]
        candidates = [make_mock_candidate(version) for version in versions]
        evaluator = CandidateEvaluator.create(
            "my-project",
            specifier=specifier,
        )
        actual = evaluator.get_applicable_candidates(candidates)
        expected_applicable = candidates[:2]
        assert [str(c.version) for c in expected_applicable] == [
            "1.10",
            "1.11",
        ]
        assert actual == expected_applicable

    @pytest.mark.parametrize(
        "specifier, expected_versions",
        [
            # Test no version constraint.
            (SpecifierSet(), ["1.0", "1.2"]),
            # Test a version constraint that excludes the candidate whose
            # hash matches.  Then the non-allowed hash is a candidate.
            (SpecifierSet("<= 1.1"), ["1.0", "1.1"]),
        ],
    )
    def test_get_applicable_candidates__hashes(
        self,
        specifier,
        expected_versions,
    ):
        """
        Test a non-None hashes value.
        """
        candidates = [
            make_mock_candidate("1.0"),
            make_mock_candidate("1.1", hex_digest=(64 * "a")),
            make_mock_candidate("1.2", hex_digest=(64 * "b")),
        ]
        hashes_data = {
            "sha256": [64 * "b"],
        }
        hashes = Hashes(hashes_data)
        evaluator = CandidateEvaluator.create(
            "my-project",
            specifier=specifier,
            hashes=hashes,
        )
        actual = evaluator.get_applicable_candidates(candidates)
        actual_versions = [str(c.version) for c in actual]
        assert actual_versions == expected_versions

    def test_compute_best_candidate(self):
        specifier = SpecifierSet("<= 1.11")
        versions = ["1.10", "1.11", "1.12"]
        candidates = [make_mock_candidate(version) for version in versions]
        evaluator = CandidateEvaluator.create(
            "my-project",
            specifier=specifier,
        )
        result = evaluator.compute_best_candidate(candidates)

        assert result._candidates == candidates
        expected_applicable = candidates[:2]
        assert [str(c.version) for c in expected_applicable] == [
            "1.10",
            "1.11",
        ]
        assert result._applicable_candidates == expected_applicable

        assert result.best_candidate is expected_applicable[1]

    def test_compute_best_candidate__none_best(self):
        """
        Test returning a None best candidate.
        """
        specifier = SpecifierSet("<= 1.10")
        versions = ["1.11", "1.12"]
        candidates = [make_mock_candidate(version) for version in versions]
        evaluator = CandidateEvaluator.create(
            "my-project",
            specifier=specifier,
        )
        result = evaluator.compute_best_candidate(candidates)

        assert result._candidates == candidates
        assert result._applicable_candidates == []
        assert result.best_candidate is None

    @pytest.mark.parametrize(
        "hex_digest, expected",
        [
            # Test a link with no hash.
            (None, 0),
            # Test a link with an allowed hash.
            (64 * "a", 1),
            # Test a link with a hash that isn't allowed.
            (64 * "b", 0),
        ],
    )
    def test_sort_key__hash(self, hex_digest, expected):
        """
        Test the effect of the link's hash on _sort_key()'s return value.
        """
        candidate = make_mock_candidate("1.0", hex_digest=hex_digest)
        hashes_data = {
            "sha256": [64 * "a"],
        }
        hashes = Hashes(hashes_data)
        evaluator = CandidateEvaluator.create("my-project", hashes=hashes)
        sort_value = evaluator._sort_key(candidate)
        # The hash is reflected in the first element of the tuple.
        actual = sort_value[0]
        assert actual == expected

    @pytest.mark.parametrize(
        "yanked_reason, expected",
        [
            # Test a non-yanked file.
            (None, 0),
            # Test a yanked file (has a lower value than non-yanked).
            ("bad metadata", -1),
        ],
    )
    def test_sort_key__is_yanked(self, yanked_reason, expected):
        """
        Test the effect of is_yanked on _sort_key()'s return value.
        """
        candidate = make_mock_candidate("1.0", yanked_reason=yanked_reason)
        evaluator = CandidateEvaluator.create("my-project")
        sort_value = evaluator._sort_key(candidate)
        # Yanked / non-yanked is reflected in the second element of the tuple.
        actual = sort_value[1]
        assert actual == expected

    def test_sort_best_candidate__no_candidates(self):
        """
        Test passing an empty list.
        """
        evaluator = CandidateEvaluator.create("my-project")
        actual = evaluator.sort_best_candidate([])
        assert actual is None

    def test_sort_best_candidate__best_yanked_but_not_all(
        self,
        caplog,
    ):
        """
        Test the best candidates being yanked, but not all.
        """
        caplog.set_level(logging.INFO)
        candidates = [
            make_mock_candidate("4.0", yanked_reason="bad metadata #4"),
            # Put the best candidate in the middle, to test sorting.
            make_mock_candidate("2.0"),
            make_mock_candidate("3.0", yanked_reason="bad metadata #3"),
            make_mock_candidate("1.0"),
        ]
        expected_best = candidates[1]
        evaluator = CandidateEvaluator.create("my-project")
        actual = evaluator.sort_best_candidate(candidates)
        assert actual is expected_best
        assert str(actual.version) == "2.0"

        # Check the log messages.
        assert len(caplog.records) == 0


class TestPackageFinder:
    @pytest.mark.parametrize(
        "allow_all_prereleases, prefer_binary",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_create__candidate_prefs(
        self,
        allow_all_prereleases,
        prefer_binary,
    ):
        """
        Test that the _candidate_prefs attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            allow_all_prereleases=allow_all_prereleases,
            prefer_binary=prefer_binary,
        )
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )
        candidate_prefs = finder._candidate_prefs
        assert candidate_prefs.allow_all_prereleases == allow_all_prereleases
        assert candidate_prefs.prefer_binary == prefer_binary

    def test_create__link_collector(self):
        """
        Test that the _link_collector attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=SelectionPreferences(allow_yanked=True),
        )

        assert finder._link_collector is link_collector

    def test_create__target_python(self):
        """
        Test that the _target_python attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        target_python = TargetPython(py_version_info=(3, 7, 3))
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=SelectionPreferences(allow_yanked=True),
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
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=SelectionPreferences(allow_yanked=True),
            target_python=None,
        )
        # Spot-check the default TargetPython object.
        actual_target_python = finder._target_python
        assert actual_target_python._given_py_version_info is None
        assert actual_target_python.py_version_info == CURRENT_PY_VERSION_INFO

    @pytest.mark.parametrize("allow_yanked", [False, True])
    def test_create__allow_yanked(self, allow_yanked):
        """
        Test that the _allow_yanked attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        selection_prefs = SelectionPreferences(allow_yanked=allow_yanked)
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )
        assert finder._allow_yanked == allow_yanked

    @pytest.mark.parametrize("ignore_requires_python", [False, True])
    def test_create__ignore_requires_python(self, ignore_requires_python):
        """
        Test that the _ignore_requires_python attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            ignore_requires_python=ignore_requires_python,
        )
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )
        assert finder._ignore_requires_python == ignore_requires_python

    def test_create__format_control(self):
        """
        Test that the format_control attribute is set correctly.
        """
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        format_control = FormatControl(set(), {":all:"})
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            format_control=format_control,
        )
        finder = PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )
        actual_format_control = finder.format_control
        assert actual_format_control is format_control
        # Check that the attributes weren't reset.
        assert actual_format_control.only_binary == {":all:"}

    @pytest.mark.parametrize(
        "allow_yanked, ignore_requires_python, only_binary, expected_formats",
        [
            (False, False, {}, frozenset({"binary", "source"})),
            # Test allow_yanked=True.
            (True, False, {}, frozenset({"binary", "source"})),
            # Test ignore_requires_python=True.
            (False, True, {}, frozenset({"binary", "source"})),
            # Test a non-trivial only_binary.
            (False, False, {"twine"}, frozenset({"binary"})),
        ],
    )
    def test_make_link_evaluator(
        self,
        allow_yanked,
        ignore_requires_python,
        only_binary,
        expected_formats,
    ):
        # Create a test TargetPython that we can check for.
        target_python = TargetPython(py_version_info=(3, 7))
        format_control = FormatControl(set(), only_binary)

        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )

        finder = PackageFinder(
            link_collector=link_collector,
            target_python=target_python,
            allow_yanked=allow_yanked,
            format_control=format_control,
            ignore_requires_python=ignore_requires_python,
        )

        # Pass a project_name that will be different from canonical_name.
        link_evaluator = finder.make_link_evaluator("Twine")

        assert link_evaluator.project_name == "Twine"
        assert link_evaluator._canonical_name == "twine"
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

    @pytest.mark.parametrize(
        "allow_all_prereleases, prefer_binary",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_make_candidate_evaluator(
        self,
        allow_all_prereleases,
        prefer_binary,
    ):
        target_python = TargetPython()
        target_python._valid_tags = [("py36", "none", "any")]
        candidate_prefs = CandidatePreferences(
            prefer_binary=prefer_binary,
            allow_all_prereleases=allow_all_prereleases,
        )
        link_collector = LinkCollector(
            session=PipSession(),
            search_scope=SearchScope([], []),
        )
        finder = PackageFinder(
            link_collector=link_collector,
            target_python=target_python,
            allow_yanked=True,
            candidate_prefs=candidate_prefs,
        )

        specifier = SpecifierSet()
        # Pass hashes to check that _hashes is set.
        hashes = Hashes({"sha256": [64 * "a"]})
        evaluator = finder.make_candidate_evaluator(
            "my-project",
            specifier=specifier,
            hashes=hashes,
        )
        assert evaluator._allow_all_prereleases == allow_all_prereleases
        assert evaluator._hashes == hashes
        assert evaluator._prefer_binary == prefer_binary
        assert evaluator._project_name == "my-project"
        assert evaluator._specifier is specifier
        assert evaluator._supported_tags == [("py36", "none", "any")]


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
    message = f"{fragment} does not match {canonical_name}"
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
