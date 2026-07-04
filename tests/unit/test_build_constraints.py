"""Tests for build constraints functionality."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from unittest import mock

from pip._internal.build_env import SubprocessBuildEnvironmentInstaller
from pip._internal.build_env.base import Prefix
from pip._internal.network.session import PipSession
from pip._internal.utils.deprecation import PipDeprecationWarning

from tests.lib import make_test_finder


class TestSubprocessBuildEnvironmentInstaller:
    """Test SubprocessBuildEnvironmentInstaller build constraint handling."""

    @mock.patch("pip._internal.build_env.installer.call_subprocess")
    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_install_ignores_regular_constraints_by_default(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        """Without build constraints, the isolated build environment ignores
        any inherited constraints (such as via PIP_CONSTRAINT) and emits no
        warning."""
        installer = SubprocessBuildEnvironmentInstaller(make_test_finder())
        prefix = Prefix(str(tmp_path))

        with warnings.catch_warnings():
            warnings.simplefilter("error", PipDeprecationWarning)
            installer.install(
                requirements=["setuptools"],
                prefix=prefix,
                kind="build dependencies",
                for_req=None,
            )

        mock_call_subprocess.assert_called_once()
        args = mock_call_subprocess.call_args.args[0]
        kwargs = mock_call_subprocess.call_args.kwargs
        assert "--use-feature" not in args
        assert kwargs.get("extra_environ") == {"_PIP_IN_BUILD_IGNORE_CONSTRAINTS": "1"}

    @mock.patch("pip._internal.build_env.installer.call_subprocess")
    @mock.patch.dict(os.environ, {"PIP_CONSTRAINT": "constraints.txt"})
    def test_install_passes_build_constraints(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        """With build constraints, each file is forwarded with --build-constraint
        and the inherited-constraint ignore flag is set, so the subprocess
        ignores inherited regular constraints and applies the build constraints
        instead."""
        installer = SubprocessBuildEnvironmentInstaller(
            make_test_finder(),
            build_constraints=["build-constraints.txt"],
        )
        prefix = Prefix(str(tmp_path))

        installer.install(
            requirements=["setuptools"],
            prefix=prefix,
            kind="build dependencies",
            for_req=None,
        )

        mock_call_subprocess.assert_called_once()
        args = mock_call_subprocess.call_args.args[0]
        kwargs = mock_call_subprocess.call_args.kwargs
        assert "--use-feature" not in args
        assert "--constraint" not in args
        assert args[args.index("--build-constraint") + 1] == "build-constraints.txt"
        assert kwargs.get("extra_environ") == {"_PIP_IN_BUILD_IGNORE_CONSTRAINTS": "1"}

    @mock.patch("pip._internal.build_env.installer.call_subprocess")
    def test_install_forwards_no_proxy_env(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        """When the parent session bypasses environment proxies, the build
        subprocess is told to do the same via --no-proxy-env."""
        session = PipSession()
        session.pip_no_proxy_env = True
        installer = SubprocessBuildEnvironmentInstaller(
            make_test_finder(session=session)
        )

        installer.install(
            requirements=["setuptools"],
            prefix=Prefix(str(tmp_path)),
            kind="build dependencies",
            for_req=None,
        )

        args = mock_call_subprocess.call_args.args[0]
        assert "--no-proxy-env" in args

    @mock.patch("pip._internal.build_env.installer.call_subprocess")
    def test_install_omits_no_proxy_env_by_default(
        self, mock_call_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        installer = SubprocessBuildEnvironmentInstaller(make_test_finder())

        installer.install(
            requirements=["setuptools"],
            prefix=Prefix(str(tmp_path)),
            kind="build dependencies",
            for_req=None,
        )

        args = mock_call_subprocess.call_args.args[0]
        assert "--no-proxy-env" not in args
