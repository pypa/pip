import logging

import pytest
from mock import patch

from pip._internal.exceptions import UnsupportedPythonVersion
from pip._internal.legacy_resolve import _check_dist_requires_python


class FakeDist(object):

    def __init__(self, project_name):
        self.project_name = project_name


@pytest.fixture
def dist():
    return FakeDist('my-project')


@patch('pip._internal.legacy_resolve.get_requires_python')
class TestCheckDistRequiresPython(object):

    """
    Test _check_dist_requires_python().
    """

    def test_compatible(self, mock_get_requires, caplog, dist):
        caplog.set_level(logging.DEBUG)
        mock_get_requires.return_value = '== 3.6.5'
        _check_dist_requires_python(
            dist,
            version_info=(3, 6, 5),
            ignore_requires_python=False,
        )
        assert not len(caplog.records)

    def test_invalid_specifier(self, mock_get_requires, caplog, dist):
        caplog.set_level(logging.DEBUG)
        mock_get_requires.return_value = 'invalid'
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

    def test_incompatible(self, mock_get_requires, dist):
        mock_get_requires.return_value = '== 3.6.4'
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

    def test_incompatible_with_ignore_requires(
        self, mock_get_requires, caplog, dist,
    ):
        caplog.set_level(logging.DEBUG)
        mock_get_requires.return_value = '== 3.6.4'
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
