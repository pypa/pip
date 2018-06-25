"""Unit Tests for pip's dependency checking logic
"""

import mock

from pip._internal.operations import check


class TestInstalledDistributionsCall(object):

    def test_passes_correct_default_kwargs(self, monkeypatch):
        my_mock = mock.MagicMock(return_value=[])
        monkeypatch.setattr(check, "get_installed_distributions", my_mock)

        check.create_package_set_from_installed()

        my_mock.assert_called_with(local_only=False, skip=())

    def test_passes_any_given_kwargs(self, monkeypatch):
        my_mock = mock.MagicMock(return_value=[])
        monkeypatch.setattr(check, "get_installed_distributions", my_mock)

        obj = object()
        check.create_package_set_from_installed(hi=obj)

        my_mock.assert_called_with(hi=obj)
