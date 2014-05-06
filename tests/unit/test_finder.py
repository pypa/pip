import pytest

import pip.wheel
import pip.pep425tags

from pkg_resources import parse_version, Distribution
from pip.log import logger
from pip.req import InstallRequirement
from pip.index import PackageFinder, Link
from pip.exceptions import (
    BestVersionAlreadyInstalled, DistributionNotFound, InstallationError,
)
from pip.util import Inf
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

    def teardown(self):
        logger.consumers = []

    def test_skip_invalid_wheel_link(self, data):
        """
        Test if PackageFinder skips invalid wheel filenames
        """
        log = []
        logger.add_consumers((logger.DEBUG, log.append))
        req = InstallRequirement.from_line("invalid")
        # data.find_links contains "invalid.whl", which is an invalid wheel
        finder = PackageFinder(
            [data.find_links],
            [],
            use_wheel=True,
            session=PipSession(),
        )
        with pytest.raises(DistributionNotFound):
            finder.find_requirement(req, True)
        "invalid.whl because the wheel filename is invalid" in "".join(log)

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
            use_wheel=True,
            session=PipSession(),
        )

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
            use_wheel=True,
            session=PipSession(),
        )
        found = finder.find_requirement(req, True)
        assert (
            found.url.endswith("simple.dist-0.1-py2.py3-none-any.whl"), found
        )

    def test_wheel_over_sdist_priority(self, data):
        """
        Test wheels have priority over sdists.
        `test_link_sorting` also covers this at lower level
        """
        req = InstallRequirement.from_line("priority")
        finder = PackageFinder(
            [data.find_links],
            [],
            use_wheel=True,
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
            use_wheel=True,
            session=PipSession(),
        )

        with pytest.raises(BestVersionAlreadyInstalled):
            finder.find_requirement(req, True)

    @patch('pip.pep425tags.supported_tags', [
        ('pyT', 'none', 'TEST'),
        ('pyT', 'TEST', 'any'),
        ('pyT', 'none', 'any'),
    ])
    def test_link_sorting(self):
        """
        Test link sorting
        """
        links = [
            (parse_version('2.0'), Link(Inf), '2.0'),
            (parse_version('2.0'), Link('simple-2.0.tar.gz'), '2.0'),
            (
                parse_version('1.0'),
                Link('simple-1.0-pyT-none-TEST.whl'),
                '1.0',
            ),
            (parse_version('1.0'), Link('simple-1.0-pyT-TEST-any.whl'), '1.0'),
            (parse_version('1.0'), Link('simple-1.0-pyT-none-any.whl'), '1.0'),
            (parse_version('1.0'), Link('simple-1.0.tar.gz'), '1.0'),
        ]

        finder = PackageFinder([], [], session=PipSession())
        finder.use_wheel = True

        results = finder._sort_versions(links)
        results2 = finder._sort_versions(sorted(links, reverse=True))

        assert links == results == results2, results2

    @patch('pip.pep425tags.supported_tags', [])
    def test_link_sorting_raises_when_wheel_unsupported(self):
        links = [
            (
                parse_version('1.0'),
                Link('simple-1.0-py2.py3-none-TEST.whl'),
                '1.0',
            ),
        ]
        finder = PackageFinder([], [], use_wheel=True, session=PipSession())
        with pytest.raises(InstallationError):
            finder._sort_versions(links)


def test_finder_priority_file_over_page(data):
    """Test PackageFinder prefers file links over equivalent page links"""
    req = InstallRequirement.from_line('gmpy==1.15', None)
    finder = PackageFinder(
        [data.find_links],
        ["http://pypi.python.org/simple"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.url.startswith("file://")


def test_finder_priority_nonegg_over_eggfragments():
    """Test PackageFinder prefers non-egg links over "#egg=" links"""
    req = InstallRequirement.from_line('bar==1.0', None)
    links = ['http://foo/bar.py#egg=bar-1.0', 'http://foo/bar-1.0.tar.gz']

    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
        link = finder.find_requirement(req, False)

    assert link.url.endswith('tar.gz')

    links.reverse()
    finder = PackageFinder(links, [], session=PipSession())

    with patch.object(finder, "_get_pages", lambda x, y: []):
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


def test_finder_installs_pre_releases(data):
    """
    Test PackageFinder finds pre-releases if asked to.
    """

    req = InstallRequirement.from_line("bar", None, prereleases=True)

    # using a local index (that has pre & dev releases)
    finder = PackageFinder([], [data.index_url("pre")], session=PipSession())
    link = finder.find_requirement(req, False)
    assert link.url.endswith("bar-2.0b1.tar.gz"), link.url

    # using find-links
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


def test_finder_installs_dev_releases(data):
    """
    Test PackageFinder finds dev releases if asked to.
    """

    req = InstallRequirement.from_line("bar", None, prereleases=True)

    # using a local index (that has dev releases)
    finder = PackageFinder([], [data.index_url("dev")], session=PipSession())
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


def test_finder_ignores_external_links(data):
    """
    Tests that PackageFinder ignores external links, with or without hashes.
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-1.0.tar.gz"


def test_finder_finds_external_links_with_hashes_per_project(data):
    """
    Tests that PackageFinder finds external links but only if they have a hash
    using the per project configuration.
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_external=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-2.0.tar.gz"


def test_finder_finds_external_links_with_hashes_all(data):
    """
    Tests that PackageFinder finds external links but only if they have a hash
    using the all externals flag.
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_all_external=True,
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-2.0.tar.gz"


def test_finder_finds_external_links_without_hashes_per_project(data):
    """
    Tests that PackageFinder finds external links if they do not have a hash
    """
    req = InstallRequirement.from_line("bar==3.0", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_external=["bar"],
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-3.0.tar.gz"


def test_finder_finds_external_links_without_hashes_all(data):
    """
    Tests that PackageFinder finds external links if they do not have a hash
    using the all external flag
    """
    req = InstallRequirement.from_line("bar==3.0", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_all_external=True,
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-3.0.tar.gz"


def test_finder_finds_external_links_without_hashes_scraped_per_project(data):
    """
    Tests that PackageFinder finds externally scraped links
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_external=["bar"],
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-4.0.tar.gz"


def test_finder_finds_external_links_without_hashes_scraped_all(data):
    """
    Tests that PackageFinder finds externally scraped links using the all
    external flag.
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_all_external=True,
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-4.0.tar.gz"


def test_finder_finds_external_links_without_hashes_per_project_all_insecure(
        data):
    """
    Tests that PackageFinder finds external links if they do not have a hash
    """
    req = InstallRequirement.from_line("bar==3.0", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_external=["bar"],
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-3.0.tar.gz"


def test_finder_finds_external_links_without_hashes_all_all_insecure(data):
    """
    Tests that PackageFinder finds external links if they do not have a hash
    using the all external flag
    """
    req = InstallRequirement.from_line("bar==3.0", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_all_external=True,
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-3.0.tar.gz"


def test_finder_finds_external_links_without_hashes_scraped_per_project_all_insecure(data):  # noqa
    """
    Tests that PackageFinder finds externally scraped links
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_external=["bar"],
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-4.0.tar.gz"


def test_finder_finds_external_links_without_hashes_scraped_all_all_insecure(
        data):
    """
    Tests that PackageFinder finds externally scraped links using the all
    external flag.
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_all_external=True,
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-4.0.tar.gz"


def test_finder_finds_external_links_without_hashes_scraped_insecure(data):
    """
    Tests that PackageFinder finds externally scraped links without the
    external flag
    """
    req = InstallRequirement.from_line("bar", None)

    # using a local index
    finder = PackageFinder(
        [],
        [data.index_url("externals")],
        allow_unverified=["bar"],
        session=PipSession(),
    )
    link = finder.find_requirement(req, False)
    assert link.filename == "bar-4.0.tar.gz"


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
            use_wheel=True,
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
