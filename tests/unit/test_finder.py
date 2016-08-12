import pytest
import sys

import pip.wheel
import pip.pep425tags

from pkg_resources import parse_version, Distribution
from pip.req import InstallRequirement
from pip.index import (
    InstallationCandidate, PackageFinder, Link, FormatControl,
    fmt_ctl_formats)
from pip.exceptions import BestVersionAlreadyInstalled, DistributionNotFound
from pip.download import PipSession

from mock import Mock, patch


def test_no_mpkg(data):
    """Finder skips zipfiles with "macosx10" in the name."""
    finder = PackageFinder([data.find_links], [], session=PipSession())
    req = InstallRequirement.from_line("pkgwithmpkg")
    found = finder.find_requirement(req, False)

    assert found.url.endswith("pkgwithmpkg-1.0.tar.gz"), found


def test_no_partial_name_match(data):
    """Finder requires the full project name to match, not just beginning."""
    finder = PackageFinder([data.find_links], [], session=PipSession())
    req = InstallRequirement.from_line("gmpy")
    found = finder.find_requirement(req, False)

    assert found.url.endswith("gmpy-1.15.tar.gz"), found


def test_tilde(data):
    """Finder can accept a path with ~ in it and will normalize it."""
    session = PipSession()
    with patch('pip.index.os.path.exists', return_value=True):
        finder = PackageFinder(['~/python-pkgs'], [], session=session)
    req = InstallRequirement.from_line("gmpy")
    with pytest.raises(DistributionNotFound):
        finder.find_requirement(req, False)


def test_duplicates_sort_ok(data):
    """Finder successfully finds one of a set of duplicates in different
    locations"""
    finder = PackageFinder(
        [data.find_links, data.find_links2],
        [],
        session=PipSession(),
    )
    req = InstallRequirement.from_line("duplicate")
    found = finder.find_requirement(req, False)

    assert found.url.endswith("duplicate-1.0.tar.gz"), found


def test_finder_detects_latest_find_links(data):
    """Test PackageFinder detects latest using find-links"""
    req = InstallRequirement.from_line('simple', None)
    finder = PackageFinder([data.find_links], [], session=PipSession())
    link = finder.find_requirement(req, False)
    assert link.url.endswith("simple-3.0.tar.gz")


def test_incorrect_case_file_index(data):
    """Test PackageFinder detects latest using wrong case"""
    req = InstallRequirement.from_line('dinner', None)
    finder = PackageFinder([], [data.find_links3], session=PipSession())
    link = finder.find_requirement(req, False)
    assert link.url.endswith("Dinner-2.0.tar.gz")


@pytest.mark.network
def test_finder_detects_latest_already_satisfied_find_links(data):
    """Test PackageFinder detects latest already satisfied using find-links"""
    req = InstallRequirement.from_line('simple', None)
    # the latest simple in local pkgs is 3.0
    latest_version = "3.0"
    satisfied_by = Mock(
        location="/path",
        parsed_version=parse_version(latest_version),
        version=latest_version
    )
    req.satisfied_by = satisfied_by
    finder = PackageFinder([data.find_links], [], session=PipSession())

    with pytest.raises(BestVersionAlreadyInstalled):
        finder.find_requirement(req, True)


@pytest.mark.network
def test_finder_detects_latest_already_satisfied_pypi_links():
    """Test PackageFinder detects latest already satisfied using pypi links"""
    req = InstallRequirement.from_line('initools', None)
    # the latest initools on pypi is 0.3.1
    latest_version = "0.3.1"
    satisfied_by = Mock(
        location="/path",
        parsed_version=parse_version(latest_version),
        version=latest_version,
    )
    req.satisfied_by = satisfied_by
    finder = PackageFinder(
        [],
        ["http://pypi.python.org/simple"],
        session=PipSession(),
    )

    with pytest.raises(BestVersionAlreadyInstalled):
        finder.find_requirement(req, True)


class TestWheel:

    def test_skip_invalid_wheel_link(self, caplog, data):
        """
        Test if PackageFinder skips invalid wheel filenames
        """
        req = InstallRequirement.from_line("invalid")
        # data.find_links contains "invalid.whl", which is an invalid wheel
        finder = PackageFinder(
            [data.find_links],
            [],
            session=PipSession(),
        )
        with pytest.raises(DistributionNotFound):
            finder.find_requirement(req, True)

        assert (
            "invalid.whl; invalid wheel filename"
            in caplog.text()
        )

    def test_not_find_wheel_not_supported(self, data, monkeypatch):
        """
        Test not finding an unsupported wheel.
        """
        monkeypatch.setattr(
            pip.pep425tags,
            "supported_tags",
            [('py1', 'none', 'any')],
        )

        req = InstallRequirement.from_line("simple.dist")
        finder = PackageFinder(
            [data.find_links],
            [],
            session=PipSession(),
        )
        finder.valid_tags = pip.pep425tags.supported_tags

        with pytest.raises(DistributionNotFound):
            finder.find_requirement(req, True)

    def test_find_wheel_supported(self, data, monkeypatch):
        """
        Test finding supported wheel.
        """
        monkeypatch.setattr(
            pip.pep425tags,
            "supported_tags",
            [('py2', 'none', 'any')],
        )

        req = InstallRequirement.from_line("simple.dist")
        finder = PackageFinder(
            [data.find_links],
            [],
            session=PipSession(),
        )
        found = finder.find_requirement(req, True)
        assert (
            found.url.endswith("simple.dist-0.1-py2.py3-none-any.whl")
        ), found

    def test_wheel_over_sdist_priority(self, data):
        """
        Test wheels have priority over sdists.
        `test_link_sorting` also covers this at lower level
        """
        req = InstallRequirement.from_line("priority")
        finder = PackageFinder(
            [data.find_links],
            [],
            session=PipSession(),
        )
        found = finder.find_requirement(req, True)
        assert found.url.endswith("priority-1.0-py2.py3-none-any.whl"), found

    def test_existing_over_wheel_priority(self, data):
        """
        Test existing install has priority over wheels.
        `test_link_sorting` also covers this at a lower level
        """
        req = InstallRequirement.from_line('priority', None)
        latest_version = "1.0"
        satisfied_by = Mock(
            location="/path",
            parsed_version=parse_version(latest_version),
            version=latest_version,
        )
        req.satisfied_by = satisfied_by
        finder = PackageFinder(
            [data.find_links],
            [],
            session=PipSession(),
        )

        with pytest.raises(BestVersionAlreadyInstalled):
            finder.find_requirement(req, True)

    def test_link_sorting(self):
        """
        Test link sorting
        """
        links = [
            InstallationCandidate("simple", "2.0", Link('simple-2.0.tar.gz')),
            InstallationCandidate(
                "simple",
                "1.0",
                Link('simple-1.0-pyT-none-TEST.whl'),
            ),
            InstallationCandidate(
                "simple",
                '1.0',
                Link('simple-1.0-pyT-TEST-any.whl'),
            ),
            InstallationCandidate(
                "simple",
                '1.0',
                Link('simple-1.0-pyT-none-any.whl'),
            ),
            InstallationCandidate(
                "simple",
                '1.0',
                Link('simple-1.0.tar.gz'),
            ),
        ]
        finder = PackageFinder([], [], session=PipSession())
        finder.valid_tags = [
            ('pyT', 'none', 'TEST'),
            ('pyT', 'TEST', 'any'),
            ('pyT', 'none', 'any'),
        ]
        results = sorted(links,
                         key=finder._candidate_sort_key, reverse=True)
        results2 = sorted(reversed(links),
                          key=finder._candidate_sort_key, reverse=True)

        assert links == results == results2, results2


def test_finder_priority_file_over_page(data):
    """Test PackageFinder prefers file links over equivalent page links"""
    req = InstallRequirement.from_line('gmpy==1.15', None)
    finder = PackageFinder(
        [data.find_links],
        ["http://pypi.python.org/simple"],
        session=PipSession(),
    )
    all_versions = finder.find_all_candidates(req.name)
    # 1 file InstallationCandidate followed by all https ones
    assert all_versions[0].location.scheme == 'file'
    assert all(version.location.scheme == 'https'
               for version in all_versions[1:]), all_versions

    link = finder.find_requirement(req, False)
    assert link.url.startswith("file://")


def test_finder_deplink():
    """
    Test PackageFinder with dependency links only
    """
    req = InstallRequirement.from_line('gmpy==1.15', None)
    finder = PackageFinder(
        [],
        [],
        process_dependency_links=True,
        session=PipSession(),
    )
    finder.add_dependency_links(
        ['https://pypi.python.org/packages/source/g/gmpy/gmpy-1.15.zip'])
    link = finder.find_requirement(req, False)
    assert link.url.startswith("https://pypi"), link


@pytest.mark.network
def test_finder_priority_page_over_deplink():
    """
    Test PackageFinder prefers page links over equivalent dependency links
    """
    req = InstallRequirement.from_line('pip==1.5.6', None)
    finder = PackageFinder(
        [],
        ["https://pypi.python.org/simple"],
        process_dependency_links=True,
        session=PipSession(),
    )
    finder.add_dependency_links([
        'https://warehouse.python.org/packages/source/p/pip/pip-1.5.6.tar.gz'])
    all_versions = finder.find_all_candidates(req.name)
    # Check that the dependency_link is last
    assert all_versions[-1].location.url.startswith('https://warehouse')
    link = finder.find_requirement(req, False)
    assert link.url.startswith("https://pypi"), link


def test_finder_priority_nonegg_over_eggfragments():
    """Test PackageFinder prefers non-egg links over "#egg=" links"""
    req = InstallRequirement.from_line('bar==1.0', None)
    links = ['http://foo/bar.py#egg=bar-1.0', 'http://foo/bar-1.0.tar.gz']

    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        all_versions = finder.find_all_candidates(req.name)
        assert all_versions[0].location.url.endswith('tar.gz')
        assert all_versions[1].location.url.endswith('#egg=bar-1.0')

        link = finder.find_requirement(req, False)

    assert link.url.endswith('tar.gz')

    links.reverse()
    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        all_versions = finder.find_all_candidates(req.name)
        assert all_versions[0].location.url.endswith('tar.gz')
        assert all_versions[1].location.url.endswith('#egg=bar-1.0')
        link = finder.find_requirement(req, False)

    assert link.url.endswith('tar.gz')


def test_finder_only_installs_stable_releases(data):
    """
    Test PackageFinder only accepts stable versioned releases by default.
    """

    req = InstallRequirement.from_line("bar", None)

    # using a local index (that has pre & dev releases)
    finder = PackageFinder([], [data.index_url("pre")], session=PipSession())
    link = finder.find_requirement(req, False)
    assert link.url.endswith("bar-1.0.tar.gz"), link.url

    # using find-links
    links = ["https://foo/bar-1.0.tar.gz", "https://foo/bar-2.0b1.tar.gz"]
    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-1.0.tar.gz"

    links.reverse()
    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-1.0.tar.gz"


def test_finder_only_installs_data_require(data):
    """
    Test whether the PackageFinder understand data-python-requires

    This can optionally be exposed by a simple-repository to tell which
    distribution are compatible with which version of Python by adding a
    data-python-require to the anchor links.

    See pep 503 for more informations.
    """

    # using a local index (that has pre & dev releases)
    finder = PackageFinder([],
                           [data.index_url("datarequire")],
                           session=PipSession())
    links = finder.find_all_candidates("fakepackage")

    expected = ['1.0.0', '9.9.9']
    if sys.version_info < (2, 7):
        expected.append('2.6.0')
    elif (2, 7) < sys.version_info < (3,):
        expected.append('2.7.0')
    elif sys.version_info > (3, 3):
        expected.append('3.3.0')

    assert set([str(v.version) for v in links]) == set(expected)


def test_finder_installs_pre_releases(data):
    """
    Test PackageFinder finds pre-releases if asked to.
    """

    req = InstallRequirement.from_line("bar", None)

    # using a local index (that has pre & dev releases)
    finder = PackageFinder(
        [], [data.index_url("pre")],
        allow_all_prereleases=True,
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.url.endswith("bar-2.0b1.tar.gz"), link.url

    # using find-links
    links = ["https://foo/bar-1.0.tar.gz", "https://foo/bar-2.0b1.tar.gz"]
    finder = PackageFinder(
        links, [],
        allow_all_prereleases=True,
        session=PipSession(),
    )

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-2.0b1.tar.gz"

    links.reverse()
    finder = PackageFinder(
        links, [],
        allow_all_prereleases=True,
        session=PipSession(),
    )

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-2.0b1.tar.gz"


def test_finder_installs_dev_releases(data):
    """
    Test PackageFinder finds dev releases if asked to.
    """

    req = InstallRequirement.from_line("bar", None)

    # using a local index (that has dev releases)
    finder = PackageFinder(
        [], [data.index_url("dev")],
        allow_all_prereleases=True,
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.url.endswith("bar-2.0.dev1.tar.gz"), link.url


def test_finder_installs_pre_releases_with_version_spec():
    """
    Test PackageFinder only accepts stable versioned releases by default.
    """
    req = InstallRequirement.from_line("bar>=0.0.dev0", None)
    links = ["https://foo/bar-1.0.tar.gz", "https://foo/bar-2.0b1.tar.gz"]

    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-2.0b1.tar.gz"

    links.reverse()
    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)
        assert link.url == "https://foo/bar-2.0b1.tar.gz"


class test_link_package_versions(object):

    # patch this for travis which has distribute in its base env for now
    @patch(
        'pip.wheel.pkg_resources.get_distribution',
        lambda x: Distribution(project_name='setuptools', version='0.9')
    )
    def setup(self):
        self.version = '1.0'
        self.parsed_version = parse_version(self.version)
        self.search_name = 'pytest'
        self.finder = PackageFinder(
            [],
            [],
            session=PipSession(),
        )

    def test_link_package_versions_match_wheel(self):
        """Test that 'pytest' archives match for 'pytest'"""

        # TODO: Uncomment these, when #1217 is fixed
        # link = Link('http:/yo/pytest-1.0.tar.gz')
        # result = self.finder._link_package_versions(link, self.search_name)
        # assert result == [(self.parsed_version, link, self.version)], result

        link = Link('http:/yo/pytest-1.0-py2.py3-none-any.whl')
        result = self.finder._link_package_versions(link, self.search_name)
        assert result == [(self.parsed_version, link, self.version)], result

    def test_link_package_versions_substring_fails(self):
        """Test that 'pytest<something> archives won't match for 'pytest'"""

        # TODO: Uncomment these, when #1217 is fixed
        # link = Link('http:/yo/pytest-xdist-1.0.tar.gz')
        # result = self.finder._link_package_versions(link, self.search_name)
        # assert result == [], result

        # link = Link('http:/yo/pytest2-1.0.tar.gz')
        # result = self.finder._link_package_versions(link, self.search_name)
        # assert result == [], result

        link = Link('http:/yo/pytest_xdist-1.0-py2.py3-none-any.whl')
        result = self.finder._link_package_versions(link, self.search_name)
        assert result == [], result


def test_get_index_urls_locations():
    """Check that the canonical name is on all indexes"""
    finder = PackageFinder(
        [], ['file://index1/', 'file://index2'], session=PipSession())
    locations = finder._get_index_urls_locations(
        InstallRequirement.from_line('Complex_Name').name)
    assert locations == ['file://index1/complex-name/',
                         'file://index2/complex-name/']


def test_find_all_candidates_nothing(data):
    """Find nothing without anything"""
    finder = PackageFinder([], [], session=PipSession())
    assert not finder.find_all_candidates('pip')


def test_find_all_candidates_find_links(data):
    finder = PackageFinder(
        [data.find_links], [], session=PipSession())
    versions = finder.find_all_candidates('simple')
    assert [str(v.version) for v in versions] == ['3.0', '2.0', '1.0']


def test_find_all_candidates_index(data):
    finder = PackageFinder(
        [], [data.index_url('simple')], session=PipSession())
    versions = finder.find_all_candidates('simple')
    assert [str(v.version) for v in versions] == ['1.0']


def test_find_all_candidates_find_links_and_index(data):
    finder = PackageFinder(
        [data.find_links], [data.index_url('simple')], session=PipSession())
    versions = finder.find_all_candidates('simple')
    # first the find-links versions then the page versions
    assert [str(v.version) for v in versions] == ['3.0', '2.0', '1.0', '1.0']


def test_fmt_ctl_matches():
    fmt = FormatControl(set(), set())
    assert fmt_ctl_formats(fmt, "fred") == frozenset(["source", "binary"])
    fmt = FormatControl(set(["fred"]), set())
    assert fmt_ctl_formats(fmt, "fred") == frozenset(["source"])
    fmt = FormatControl(set(["fred"]), set([":all:"]))
    assert fmt_ctl_formats(fmt, "fred") == frozenset(["source"])
    fmt = FormatControl(set(), set(["fred"]))
    assert fmt_ctl_formats(fmt, "fred") == frozenset(["binary"])
    fmt = FormatControl(set([":all:"]), set(["fred"]))
    assert fmt_ctl_formats(fmt, "fred") == frozenset(["binary"])
