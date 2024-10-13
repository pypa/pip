import email.message
import logging
import os
from typing import List, Optional, Type, TypeVar, cast
from unittest import mock

import pytest

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName

from pip._internal.exceptions import (
    InstallationError,
    NoneMetadataError,
    UnsupportedPythonVersion,
)
from pip._internal.metadata import BaseDistribution
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.legacy.resolver import (
    Resolver,
    _check_dist_requires_python,
)

from tests.lib import TestData, make_test_finder
from tests.lib.index import make_mock_candidate

T = TypeVar("T")


class FakeDist(BaseDistribution):
    def __init__(self, metadata: email.message.Message) -> None:
        self._canonical_name = cast(NormalizedName, "my-project")
        self._metadata = metadata

    def __str__(self) -> str:
        return f"<distribution {self.canonical_name!r}>"

    @property
    def canonical_name(self) -> NormalizedName:
        return self._canonical_name

    @property
    def metadata(self) -> email.message.Message:
        return self._metadata


def make_fake_dist(
    *, klass: Type[BaseDistribution] = FakeDist, requires_python: Optional[str] = None
) -> BaseDistribution:
    metadata = email.message.Message()
    metadata["Name"] = "my-project"
    if requires_python is not None:
        metadata["Requires-Python"] = requires_python

    # Too many arguments for "BaseDistribution"
    return klass(metadata)  # type: ignore[call-arg]


def make_test_resolver(
    monkeypatch: pytest.MonkeyPatch,
    mock_candidates: List[InstallationCandidate],
) -> Resolver:
    def _find_candidates(project_name: str) -> List[InstallationCandidate]:
        return mock_candidates

    finder = make_test_finder()
    monkeypatch.setattr(finder, "find_all_candidates", _find_candidates)

    return Resolver(
        finder=finder,
        preparer=mock.Mock(),  # Not used.
        make_install_req=install_req_from_line,
        wheel_cache=None,
        use_user_site=False,
        force_reinstall=False,
        ignore_dependencies=False,
        ignore_installed=False,
        ignore_requires_python=False,
        upgrade_strategy="to-satisfy-only",
    )


class TestAddRequirement:
    """
    Test _add_requirement_to_set().
    """

    def test_unsupported_wheel_link_requirement_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN
        resolver = make_test_resolver(monkeypatch, [])
        requirement_set = RequirementSet(check_supported_wheels=True)

        install_req = install_req_from_line(
            "https://whatever.com/peppercorn-0.4-py2.py3-bogus-any.whl",
        )
        assert install_req.link is not None
        assert install_req.link.is_wheel
        assert install_req.link.scheme == "https"

        # WHEN / THEN
        with pytest.raises(InstallationError):
            resolver._add_requirement_to_set(requirement_set, install_req)

    def test_unsupported_wheel_local_file_requirement_raises(
        self, data: TestData, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GIVEN
        resolver = make_test_resolver(monkeypatch, [])
        requirement_set = RequirementSet(check_supported_wheels=True)

        install_req = install_req_from_line(
            os.fspath(data.packages.joinpath("simple.dist-0.1-py1-none-invalid.whl")),
        )
        assert install_req.link is not None
        assert install_req.link.is_wheel
        assert install_req.link.scheme == "file"

        # WHEN / THEN
        with pytest.raises(InstallationError):
            resolver._add_requirement_to_set(requirement_set, install_req)

    def test_exclusive_environment_markers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Make sure excluding environment markers are handled correctly."""
        # GIVEN
        resolver = make_test_resolver(monkeypatch, [])
        requirement_set = RequirementSet(check_supported_wheels=True)

        eq36 = install_req_from_line("Django>=1.6.10,<1.7 ; python_version == '3.6'")
        eq36.user_supplied = True
        ne36 = install_req_from_line("Django>=1.6.10,<1.8 ; python_version != '3.6'")
        ne36.user_supplied = True

        # WHEN
        resolver._add_requirement_to_set(requirement_set, eq36)
        resolver._add_requirement_to_set(requirement_set, ne36)

        # THEN
        assert requirement_set.has_requirement("Django")
        assert len(requirement_set.all_requirements) == 1


class TestCheckDistRequiresPython:
    """
    Test _check_dist_requires_python().
    """

    def test_compatible(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Test a Python version compatible with the dist's Requires-Python.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist(requires_python="== 3.6.5")

        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert not len(caplog.records)

    def test_incompatible(self) -> None:
        """
        Test a Python version incompatible with the dist's Requires-Python.
        """
        dist = make_fake_dist(requires_python="== 3.6.4")
        with pytest.raises(UnsupportedPythonVersion) as exc:
            _check_dist_requires_python(
                dist,
                version_info=(3, 6, 5),
                ignore_requires_python=False,
            )
        assert str(exc.value) == (
            "Package 'my-project' requires a different Python: "
            "3.6.5 not in '==3.6.4'"
        )

    def test_incompatible_with_ignore_requires(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test a Python version incompatible with the dist's Requires-Python
        while passing ignore_requires_python=True.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist(requires_python="== 3.6.4")
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=True,
        )
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "DEBUG"
        assert record.message == (
            "Ignoring failed Requires-Python check for package 'my-project': "
            "3.6.5 not in '==3.6.4'"
        )

    def test_none_requires_python(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Test a dist with Requires-Python None.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist()
        # Make sure our test setup is correct.
        assert dist.requires_python == SpecifierSet()
        assert len(caplog.records) == 0

        # Then there is no exception and no log message.
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert len(caplog.records) == 0

    def test_invalid_requires_python(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Test a dist with an invalid Requires-Python.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist(requires_python="invalid")
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert record.message == (
            "Package 'my-project' has an invalid Requires-Python: "
            "Invalid specifier: 'invalid'"
        )

    @pytest.mark.parametrize(
        "metadata_name",
        [
            "METADATA",
            "PKG-INFO",
        ],
    )
    def test_empty_metadata_error(self, metadata_name: str) -> None:
        """Test dist.metadata raises FileNotFoundError."""

        class NotWorkingFakeDist(FakeDist):
            @property
            def metadata(self) -> email.message.Message:
                raise FileNotFoundError(metadata_name)

        dist = make_fake_dist(klass=NotWorkingFakeDist)  # type: ignore

        with pytest.raises(NoneMetadataError) as exc:
            _check_dist_requires_python(
                dist,
                version_info=(3, 6, 5),
                ignore_requires_python=False,
            )
        assert str(exc.value) == (
            f"None {metadata_name} metadata found for distribution: "
            "<distribution 'my-project'>"
        )


class TestYankedWarning:
    """
    Test _populate_link() emits warning if one or more candidates are yanked.
    """

    def test_sort_best_candidate__has_non_yanked(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Test unyanked candidate preferred over yanked.
        """
        # Ignore spurious DEBUG level messages
        # TODO: Probably better to work out why they are occurring, but IMO the
        #       tests are at fault here for being to dependent on exact output.
        caplog.set_level(logging.WARNING)
        candidates = [
            make_mock_candidate("1.0"),
            make_mock_candidate("2.0", yanked_reason="bad metadata #2"),
        ]
        ireq = install_req_from_line("pkg")

        resolver = make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[0].link
        assert len(caplog.records) == 0

    def test_sort_best_candidate__all_yanked(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Test all candidates yanked.
        """
        # Ignore spurious DEBUG level messages
        # TODO: Probably better to work out why they are occurring, but IMO the
        #       tests are at fault here for being to dependent on exact output.
        caplog.set_level(logging.WARNING)
        candidates = [
            make_mock_candidate("1.0", yanked_reason="bad metadata #1"),
            # Put the best candidate in the middle, to test sorting.
            make_mock_candidate("3.0", yanked_reason="bad metadata #3"),
            make_mock_candidate("2.0", yanked_reason="bad metadata #2"),
        ]
        ireq = install_req_from_line("pkg")

        resolver = make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[1].link

        # Check the log messages.
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert record.message == (
            "The candidate selected for download or install is a yanked "
            "version: 'mypackage' candidate "
            "(version 3.0 at https://example.com/pkg-3.0.tar.gz)\n"
            "Reason for being yanked: bad metadata #3"
        )

    @pytest.mark.parametrize(
        "yanked_reason, expected_reason",
        [
            # Test no reason given.
            ("", "<none given>"),
            # Test a unicode string with a non-ascii character.
            ("curly quote: \u2018", "curly quote: \u2018"),
        ],
    )
    def test_sort_best_candidate__yanked_reason(
        self,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        yanked_reason: str,
        expected_reason: str,
    ) -> None:
        """
        Test the log message with various reason strings.
        """
        # Ignore spurious DEBUG level messages
        # TODO: Probably better to work out why they are occurring, but IMO the
        #       tests are at fault here for being to dependent on exact output.
        caplog.set_level(logging.WARNING)
        candidates = [
            make_mock_candidate("1.0", yanked_reason=yanked_reason),
        ]
        ireq = install_req_from_line("pkg")

        resolver = make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[0].link

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        expected_message = (
            "The candidate selected for download or install is a yanked "
            "version: 'mypackage' candidate "
            "(version 1.0 at https://example.com/pkg-1.0.tar.gz)\n"
            "Reason for being yanked: "
        ) + expected_reason
        assert record.message == expected_message
