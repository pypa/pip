"""Tests for build constraints functionality."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from pip._internal.build_env import SubprocessBuildEnvironmentInstaller, _Prefix
from pip._internal.utils.deprecation import PipDeprecationWarning

from tests.lib import make_test_finder


class TestSubprocessBuildEnvironmentInstaller:
    """Test SubprocessBuildEnvironmentInstaller build constraints functionality."""

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_deprecation_check_no_pip_constraint(self) -> None:
        """Test no deprecation warning is shown when PIP_CONSTRAINT is not set."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraints.txt"],
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_feature_enabled(self) -> None:
        """
        Test no deprecation warning is shown when
        build-constraint feature is enabled
        """
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraints.txt"],
            build_constraint_feature_enabled=True,
        )

        # Should not raise any warning
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_constraint_mismatch(self) -> None:
        """
        Test no deprecation warning is shown when
        PIP_CONSTRAINT doesn't match regular constraints.
        """
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["different.txt"],
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning
        installer._deprecation_constraint_check()

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_deprecation_check_warning_shown(self) -> None:
        """Test deprecation warning is shown when conditions are met."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraints.txt"],
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

    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraint1.txt constraint2.txt"})
    def test_deprecation_check_multiple_constraints(self) -> None:
        """Test deprecation warning works with multiple constraints."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraint1.txt", "constraint2.txt"],
            build_constraint_feature_enabled=False,
        )

        with pytest.warns(PipDeprecationWarning):
            installer._deprecation_constraint_check()

    @mock.patch.dict(
        os.environ, {"PIP_CONSTRAINT": "constraint1.txt constraint2.txt extra.txt"}
    )
    def test_deprecation_check_partial_match_no_warning(self) -> None:
        """Test no deprecation warning is shown when only partial match."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraint1.txt", "constraint2.txt"],
            build_constraint_feature_enabled=False,
        )

        # Should not raise any warning since PIP_CONSTRAINT has extra file
        installer._deprecation_constraint_check()

    @mock.patch("pip._internal.build_env.call_subprocess")
    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_install_calls_deprecation_check(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        """Test install method calls deprecation check."""
        finder = make_test_finder()
        installer = SubprocessBuildEnvironmentInstaller(
            finder,
            constraints=["constraints.txt"],
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
