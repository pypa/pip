import logging

import mock
import pytest
from pip._vendor import pkg_resources

from pip._internal.exceptions import NoneMetadataError, UnsupportedPythonVersion
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.legacy.resolver import (
    Resolver,
    _check_dist_requires_python,
)
from pip._internal.utils.packaging import get_requires_python
from tests.lib import make_test_finder
from tests.lib.index import make_mock_candidate


# We need to inherit from DistInfoDistribution for the `isinstance()`
# check inside `packaging.get_metadata()` to work.
class FakeDist(pkg_resources.DistInfoDistribution):

    def __init__(self, metadata, metadata_name=None):
        """
        :param metadata: The value that dist.get_metadata() should return
            for the `metadata_name` metadata.
        :param metadata_name: The name of the metadata to store
            (can be "METADATA" or "PKG-INFO").  Defaults to "METADATA".
        """
        if metadata_name is None:
            metadata_name = 'METADATA'

        self.project_name = 'my-project'
        self.metadata_name = metadata_name
        self.metadata = metadata

    def __str__(self):
        return '<distribution {!r}>'.format(self.project_name)

    def has_metadata(self, name):
        return (name == self.metadata_name)

    def get_metadata(self, name):
        assert name == self.metadata_name
        return self.metadata


def make_fake_dist(requires_python=None, metadata_name=None):
    metadata = 'Name: test\n'
    if requires_python is not None:
        metadata += 'Requires-Python:{}'.format(requires_python)

    return FakeDist(metadata, metadata_name=metadata_name)


class TestCheckDistRequiresPython(object):

    """
    Test _check_dist_requires_python().
    """

    def test_compatible(self, caplog):
        """
        Test a Python version compatible with the dist's Requires-Python.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist('== 3.6.5')

        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert not len(caplog.records)

    def test_incompatible(self):
        """
        Test a Python version incompatible with the dist's Requires-Python.
        """
        dist = make_fake_dist('== 3.6.4')
        with pytest.raises(UnsupportedPythonVersion) as exc:
            _check_dist_requires_python(
                dist,
                version_info=(3, 6, 5),
                ignore_requires_python=False,
            )
        assert str(exc.value) == (
            "Package 'my-project' requires a different Python: "
            "3.6.5 not in '== 3.6.4'"
        )

    def test_incompatible_with_ignore_requires(self, caplog):
        """
        Test a Python version incompatible with the dist's Requires-Python
        while passing ignore_requires_python=True.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist('== 3.6.4')
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=True,
        )
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == 'DEBUG'
        assert record.message == (
            "Ignoring failed Requires-Python check for package 'my-project': "
            "3.6.5 not in '== 3.6.4'"
        )

    def test_none_requires_python(self, caplog):
        """
        Test a dist with Requires-Python None.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist()
        # Make sure our test setup is correct.
        assert get_requires_python(dist) is None
        assert len(caplog.records) == 0

        # Then there is no exception and no log message.
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert len(caplog.records) == 0

    def test_invalid_requires_python(self, caplog):
        """
        Test a dist with an invalid Requires-Python.
        """
        caplog.set_level(logging.DEBUG)
        dist = make_fake_dist('invalid')
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == 'WARNING'
        assert record.message == (
            "Package 'my-project' has an invalid Requires-Python: "
            "Invalid specifier: 'invalid'"
        )

    @pytest.mark.parametrize('metadata_name', [
        'METADATA',
        'PKG-INFO',
    ])
    def test_empty_metadata_error(self, caplog, metadata_name):
        """
        Test dist.has_metadata() returning True and dist.get_metadata()
        returning None.
        """
        dist = make_fake_dist(metadata_name=metadata_name)
        dist.metadata = None

        # Make sure our test setup is correct.
        assert dist.has_metadata(metadata_name)
        assert dist.get_metadata(metadata_name) is None

        with pytest.raises(NoneMetadataError) as exc:
            _check_dist_requires_python(
                dist,
                version_info=(3, 6, 5),
                ignore_requires_python=False,
            )
        assert str(exc.value) == (
            "None {} metadata found for distribution: "
            "<distribution 'my-project'>".format(metadata_name)
        )


class TestYankedWarning(object):
    """
    Test _populate_link() emits warning if one or more candidates are yanked.
    """
    def _make_test_resolver(self, monkeypatch, mock_candidates):
        def _find_candidates(project_name):
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

    def test_sort_best_candidate__has_non_yanked(self, caplog, monkeypatch):
        """
        Test unyanked candidate preferred over yanked.
        """
        candidates = [
            make_mock_candidate('1.0'),
            make_mock_candidate('2.0', yanked_reason='bad metadata #2'),
        ]
        ireq = install_req_from_line("pkg")

        resolver = self._make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[0].link
        assert len(caplog.records) == 0

    def test_sort_best_candidate__all_yanked(self, caplog, monkeypatch):
        """
        Test all candidates yanked.
        """
        candidates = [
            make_mock_candidate('1.0', yanked_reason='bad metadata #1'),
            # Put the best candidate in the middle, to test sorting.
            make_mock_candidate('3.0', yanked_reason='bad metadata #3'),
            make_mock_candidate('2.0', yanked_reason='bad metadata #2'),
        ]
        ireq = install_req_from_line("pkg")

        resolver = self._make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[1].link

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
    def test_sort_best_candidate__yanked_reason(
        self, caplog, monkeypatch, yanked_reason, expected_reason,
    ):
        """
        Test the log message with various reason strings.
        """
        candidates = [
            make_mock_candidate('1.0', yanked_reason=yanked_reason),
        ]
        ireq = install_req_from_line("pkg")

        resolver = self._make_test_resolver(monkeypatch, candidates)
        resolver._populate_link(ireq)

        assert ireq.link == candidates[0].link

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
