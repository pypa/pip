"""Tests for build constraints functionality."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from unittest import mock

import pytest

from pip._internal.build_env import SubprocessBuildEnvironmentInstaller, _Prefix
from pip._internal.utils.deprecation import PipDeprecationWarning

from tests.lib import make_test_finder


class TestSubprocessBuildEnvironmentInstaller:
    """Test SubprocessBuildEnvironmentInstaller build constraints functionality."""

    def setup_method(self) -> None:
        """Reset the global deprecation warning flag before each test."""
        import pip._internal.build_env

        pip._internal.build_env._DEPRECATION_WARNING_SHOWN = False

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_deprecation_check_no_pip_constraint(self) -> None:
        """Test no deprecation warning when PIP_CONSTRAINT is not set."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": ""})
    def test_deprecation_check_empty_pip_constraint(self) -> None:
        """Test no deprecation warning for empty PIP_CONSTRAINT."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning since PIP_CONSTRAINT is empty
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "   "})
    def test_deprecation_check_whitespace_pip_constraint(self) -> None:
        """Test no deprecation warning for whitespace-only PIP_CONSTRAINT."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning since PIP_CONSTRAINT is only whitespace
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_feature_enabled(self) -> None:
        """Test no deprecation warning when build-constraint feature is enabled."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=True,
        )

        # Should not raise any warning
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_warning_shown(self) -> None:
        """Test deprecation warning emitted when PIP_CONSTRAINT is set
        and build-constraint is not enabled."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )

        with pytest.warns(PipDeprecationWarning) as warning_info:
            installer._deprecation_constraint_check()

        assert len(warning_info) == 1
        message = str(warning_info[0].message)
        assert (
            "Setting PIP_CONSTRAINT will not affect build constraints in the future"
            in message
        )
        assert (
            "to specify build constraints using "
            "--build-constraint or PIP_BUILD_CONSTRAINT" in message
        )

    @mock.patch("pip._internal.build_env.call_subprocess")
    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_install_calls_deprecation_check(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        """Test install method calls deprecation check and proceeds with warning."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )
        prefix = _Prefix(str(tmp_path))

        with pytest.warns(PipDeprecationWarning):
            installer.install(
                requirements=["setuptools"],
                prefix=prefix,
                kind="build dependencies",
                for_req=None,
            )

        # Verify that call_subprocess was called (install proceeded after warning)
        mock_call_subprocess.assert_called_once()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_warning_shown_only_once(self) -> None:
        """Test deprecation warning is shown only once per process."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            build_constraint_feature_enabled=False,
        )

        with pytest.warns(PipDeprecationWarning):
            installer._deprecation_constraint_check()

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            installer._deprecation_constraint_check()
        assert len(warning_list) == 0
