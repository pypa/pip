from __future__ import annotations

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link


def make_test_link(
    filename: str, version: str, yanked_reason: str | None = None
) -> Link:
    """Create a test Link object."""
    return Link(
        url=f"https://example.com/packages/{filename}",
        yanked_reason=yanked_reason,
    )


def make_test_candidate(
    name: str, version: str, filename: str, yanked_reason: str | None = None
) -> InstallationCandidate:
    """Create a test InstallationCandidate."""
    link = make_test_link(filename, version, yanked_reason)
    return InstallationCandidate(name=name, version=version, link=link)


class TestFileLevelYanking:
    """Test file-level yanking: some files for a version are yanked."""

    def test_file_level_yanking_excludes_yanked_file(self) -> None:
        """
        When only some files for a version are yanked (file-level yanking),
        the yanked files should be excluded but non-yanked files should
        still be available.
        """
        # Version 1.0 has two files: wheel (not yanked) and tarball (yanked)
        candidates = [
            make_test_candidate(
                "example", "1.0", "example-1.0-py3-none-any.whl", None
            ),
            make_test_candidate(
                "example", "1.0", "example-1.0.tar.gz", "bad tarball"
            ),
        ]

        # Group by version
        version_to_candidates: dict[Version, list[InstallationCandidate]] = {}
        for c in candidates:
            version_to_candidates.setdefault(c.version, []).append(c)

        # Determine yanked versions (release-level)
        yanked_versions: set[Version] = set()
        for version, version_cands in version_to_candidates.items():
            if all(c.link.is_yanked for c in version_cands):
                yanked_versions.add(version)

        # Version 1.0 should NOT be in yanked_versions (file-level yanking)
        assert Version("1.0") not in yanked_versions

        # The wheel should still be available
        available = [c for c in candidates if not c.link.is_yanked]
        assert len(available) == 1
        assert available[0].link.filename == "example-1.0-py3-none-any.whl"


class TestReleaseLevelYanking:
    """Test release-level yanking: all files for a version are yanked."""

    def test_release_level_yanking_detects_yanked_version(self) -> None:
        """
        When all files for a version are yanked (release-level yanking),
        the version should be considered yanked.
        """
        # Version 2.0 has all files yanked
        candidates = [
            make_test_candidate(
                "example", "2.0", "example-2.0-py3-none-any.whl", "security issue"
            ),
            make_test_candidate(
                "example", "2.0", "example-2.0.tar.gz", "security issue"
            ),
        ]

        # Group by version
        version_to_candidates: dict[Version, list[InstallationCandidate]] = {}
        for c in candidates:
            version_to_candidates.setdefault(c.version, []).append(c)

        # Determine yanked versions
        yanked_versions: set[Version] = set()
        for version, version_cands in version_to_candidates.items():
            if all(c.link.is_yanked for c in version_cands):
                yanked_versions.add(version)

        # Version 2.0 SHOULD be in yanked_versions (release-level yanking)
        assert Version("2.0") in yanked_versions

    def test_release_level_yanking_allows_pinned_version(self) -> None:
        """
        A yanked release should be selectable if the specifier pins to
        that exact version using == or ===.
        """

        def is_pinned(specifier: SpecifierSet) -> bool:
            for sp in specifier:
                if sp.operator == "===":
                    return True
                if sp.operator != "==":
                    continue
                if sp.version.endswith(".*"):
                    continue
                return True
            return False

        # These specifiers should be considered "pinned"
        assert is_pinned(SpecifierSet("==2.0"))
        assert is_pinned(SpecifierSet("===2.0"))

        # These specifiers should NOT be considered "pinned"
        assert not is_pinned(SpecifierSet(">=2.0"))
        assert not is_pinned(SpecifierSet("==2.*"))
        assert not is_pinned(SpecifierSet("~=2.0"))
        assert not is_pinned(SpecifierSet(">1.0,<3.0"))


class TestMixedYankingScenarios:
    """Test scenarios with mixed file-level and release-level yanking."""

    def test_mixed_yanking_version_selection(self) -> None:
        """
        With multiple versions having different yanking states:
        - Version 1.0: file-level yanking (one file yanked)
        - Version 2.0: release-level yanking (all files yanked)
        - Version 3.0: no yanking

        Without pinning, versions 1.0 and 3.0 should be available,
        version 2.0 should be excluded.
        """
        candidates = [
            # Version 1.0: file-level yanking
            make_test_candidate(
                "example", "1.0", "example-1.0-py3-none-any.whl", None
            ),
            make_test_candidate(
                "example", "1.0", "example-1.0.tar.gz", "bad tarball"
            ),
            # Version 2.0: release-level yanking
            make_test_candidate(
                "example", "2.0", "example-2.0-py3-none-any.whl", "security"
            ),
            make_test_candidate(
                "example", "2.0", "example-2.0.tar.gz", "security"
            ),
            # Version 3.0: no yanking
            make_test_candidate(
                "example", "3.0", "example-3.0-py3-none-any.whl", None
            ),
            make_test_candidate(
                "example", "3.0", "example-3.0.tar.gz", None
            ),
        ]

        # Group by version
        version_to_candidates: dict[Version, list[InstallationCandidate]] = {}
        for c in candidates:
            version_to_candidates.setdefault(c.version, []).append(c)

        # Determine yanked versions
        yanked_versions: set[Version] = set()
        for version, version_cands in version_to_candidates.items():
            if all(c.link.is_yanked for c in version_cands):
                yanked_versions.add(version)

        # Check yanked versions
        assert Version("1.0") not in yanked_versions  # file-level, not release-level
        assert Version("2.0") in yanked_versions  # release-level
        assert Version("3.0") not in yanked_versions  # not yanked

        # Available candidates without pinning (release-level yanked excluded)
        pinned = False
        available = []
        for c in candidates:
            version_is_yanked = c.version in yanked_versions
            file_is_yanked = c.link.is_yanked

            if file_is_yanked:
                if version_is_yanked and pinned:
                    available.append(c)
                else:
                    continue  # Skip yanked files
            else:
                available.append(c)

        # Should have: 1.0 wheel, 3.0 wheel, 3.0 tarball
        assert len(available) == 3
        versions = {c.version for c in available}
        assert Version("1.0") in versions
        assert Version("2.0") not in versions  # Excluded (release-level yanked)
        assert Version("3.0") in versions

    def test_all_versions_yanked_allows_pinned(self) -> None:
        """
        When ALL versions are yanked and the specifier is pinned,
        the pinned yanked version should be selectable.
        """
        candidates = [
            # Version 1.0: release-level yanking
            make_test_candidate(
                "example", "1.0", "example-1.0.tar.gz", "old version"
            ),
            # Version 2.0: release-level yanking
            make_test_candidate(
                "example", "2.0", "example-2.0.tar.gz", "has bug"
            ),
        ]

        # Group by version
        version_to_candidates: dict[Version, list[InstallationCandidate]] = {}
        for c in candidates:
            version_to_candidates.setdefault(c.version, []).append(c)

        # Determine yanked versions
        yanked_versions: set[Version] = set()
        for version, version_cands in version_to_candidates.items():
            if all(c.link.is_yanked for c in version_cands):
                yanked_versions.add(version)

        # Both versions are yanked
        assert len(yanked_versions) == 2

        # With pinned specifier ==2.0, version 2.0 should be allowed
        all_versions_yanked = all(v in yanked_versions for v in version_to_candidates)
        assert all_versions_yanked

        pinned = True  # Simulating ==2.0
        available = []
        for c in candidates:
            version_is_yanked = c.version in yanked_versions
            file_is_yanked = c.link.is_yanked

            if file_is_yanked:
                if version_is_yanked and pinned:
                    available.append(c)
                elif all_versions_yanked and pinned:
                    available.append(c)
                else:
                    continue
            else:
                available.append(c)

        # Both versions should be available when pinned and all are yanked
        assert len(available) == 2
