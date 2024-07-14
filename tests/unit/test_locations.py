"""
locations.py tests

"""

import getpass
import os
import shutil
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from pip._internal.locations import SCHEME_KEYS, _should_use_sysconfig, get_scheme

if sys.platform == "win32":
    pwd = Mock()
else:
    import pwd


def _get_scheme_dict(*args: Any, **kwargs: Any) -> Dict[str, str]:
    scheme = get_scheme(*args, **kwargs)
    return {k: getattr(scheme, k) for k in SCHEME_KEYS}


class TestLocations:
    def setup_method(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.st_uid = 9999
        self.username = "example"
        self.patch()

    def teardown_method(self) -> None:
        self.revert_patch()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def patch(self) -> None:
        """first store and then patch python methods pythons"""
        self.tempfile_gettempdir = tempfile.gettempdir
        self.old_os_fstat = os.fstat
        if sys.platform != "win32":
            # os.geteuid and pwd.getpwuid are not implemented on windows
            self.old_os_geteuid = os.geteuid
            self.old_pwd_getpwuid = pwd.getpwuid
        self.old_getpass_getuser = getpass.getuser

        # now patch
        tempfile.gettempdir = lambda: self.tempdir
        getpass.getuser = lambda: self.username
        os.fstat = lambda fd: self.get_mock_fstat(fd)
        if sys.platform != "win32":
            os.geteuid = lambda: self.st_uid
            pwd.getpwuid = self.get_mock_getpwuid

    def revert_patch(self) -> None:
        """revert the patches to python methods"""
        tempfile.gettempdir = self.tempfile_gettempdir
        getpass.getuser = self.old_getpass_getuser
        if sys.platform != "win32":
            # os.geteuid and pwd.getpwuid are not implemented on windows
            os.geteuid = self.old_os_geteuid
            pwd.getpwuid = self.old_pwd_getpwuid
        os.fstat = self.old_os_fstat

    def get_mock_fstat(self, fd: int) -> os.stat_result:
        """returns a basic mock fstat call result.
        Currently only the st_uid attribute has been set.
        """
        result = Mock()
        result.st_uid = self.st_uid
        return result

    def get_mock_getpwuid(self, uid: int) -> Any:
        """returns a basic mock pwd.getpwuid call result.
        Currently only the pw_name attribute has been set.
        """
        result = Mock()
        result.pw_name = self.username
        return result

    def test_default_should_use_sysconfig(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(sysconfig, "_PIP_USE_SYSCONFIG", raising=False)
        if sys.version_info[:2] >= (3, 10):
            assert _should_use_sysconfig() is True
        else:
            assert _should_use_sysconfig() is False

    @pytest.mark.parametrize("vendor_value", [True, False, None, "", 0, 1])
    def test_vendor_overriden_should_use_sysconfig(
        self, monkeypatch: pytest.MonkeyPatch, vendor_value: Any
    ) -> None:
        monkeypatch.setattr(
            sysconfig, "_PIP_USE_SYSCONFIG", vendor_value, raising=False
        )
        assert _should_use_sysconfig() is bool(vendor_value)


class TestDistutilsScheme:
    def test_root_modifies_appropriately(self) -> None:
        # This deals with nt/posix path differences
        # root is c:\somewhere\else or /somewhere/else
        root = os.path.normcase(
            os.path.abspath(os.path.join(os.path.sep, "somewhere", "else"))
        )
        norm_scheme = _get_scheme_dict("example")
        root_scheme = _get_scheme_dict("example", root=root)

        for key, value in norm_scheme.items():
            drive, path = os.path.splitdrive(os.path.abspath(value))
            expected = os.path.join(root, path[1:])
            assert os.path.abspath(root_scheme[key]) == expected

    @pytest.mark.incompatible_with_sysconfig
    @pytest.mark.incompatible_with_venv
    def test_distutils_config_file_read(
        self, tmpdir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This deals with nt/posix path differences
        install_scripts = os.path.normcase(
            os.path.abspath(os.path.join(os.path.sep, "somewhere", "else"))
        )
        f = tmpdir / "config" / "setup.cfg"
        f.parent.mkdir()
        f.write_text("[install]\ninstall-scripts=" + install_scripts)
        from distutils.dist import Distribution

        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            "find_config_files",
            lambda self: [f],
        )
        scheme = _get_scheme_dict("example")
        assert scheme["scripts"] == install_scripts

    @pytest.mark.incompatible_with_sysconfig
    @pytest.mark.incompatible_with_venv
    # when we request install-lib, we should install everything (.py &
    # .so) into that path; i.e. ensure platlib & purelib are set to
    # this path. sysconfig does not support this.
    def test_install_lib_takes_precedence(
        self, tmpdir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This deals with nt/posix path differences
        install_lib = os.path.normcase(
            os.path.abspath(os.path.join(os.path.sep, "somewhere", "else"))
        )
        f = tmpdir / "config" / "setup.cfg"
        f.parent.mkdir()
        f.write_text("[install]\ninstall-lib=" + install_lib)
        from distutils.dist import Distribution

        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            "find_config_files",
            lambda self: [f],
        )
        scheme = _get_scheme_dict("example")
        assert scheme["platlib"] == install_lib + os.path.sep
        assert scheme["purelib"] == install_lib + os.path.sep

    def test_prefix_modifies_appropriately(self) -> None:
        prefix = os.path.abspath(os.path.join("somewhere", "else"))

        normal_scheme = _get_scheme_dict("example")
        prefix_scheme = _get_scheme_dict("example", prefix=prefix)

        def _calculate_expected(value: str) -> str:
            path = os.path.join(prefix, os.path.relpath(value, sys.prefix))
            return os.path.normpath(path)

        expected = {k: _calculate_expected(v) for k, v in normal_scheme.items()}
        assert prefix_scheme == expected
