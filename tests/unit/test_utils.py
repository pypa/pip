"""
util tests

"""

import os
import shutil
import stat
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterator, List, NoReturn, Optional, Tuple, Type
from unittest.mock import Mock

import pytest

from pip._vendor.packaging.requirements import Requirement

from pip._internal.exceptions import HashMismatch, HashMissing, InstallationError
from pip._internal.utils.deprecation import PipDeprecationWarning, deprecated
from pip._internal.utils.egg_link import egg_link_path_from_location
from pip._internal.utils.glibc import (
    glibc_version_string,
    glibc_version_string_confstr,
    glibc_version_string_ctypes,
)
from pip._internal.utils.hashes import Hashes, MissingHashes
from pip._internal.utils.misc import (
    HiddenText,
    build_netloc,
    build_url_from_netloc,
    format_size,
    get_prog,
    hide_url,
    hide_value,
    is_console_interactive,
    normalize_path,
    normalize_version_info,
    parse_netloc,
    redact_auth_from_requirement,
    redact_auth_from_url,
    redact_netloc,
    remove_auth_from_url,
    rmtree,
    rmtree_errorhandler,
    split_auth_from_netloc,
    split_auth_netloc_from_url,
    tabulate,
)
from pip._internal.utils.setuptools_build import make_setuptools_shim_args


class Tests_EgglinkPath:
    "util.egg_link_path_from_location() tests"

    def setup_method(self) -> None:
        project = "foo"

        self.mock_dist = Mock(project_name=project)
        self.site_packages = "SITE_PACKAGES"
        self.user_site = "USER_SITE"
        self.user_site_egglink = os.path.join(self.user_site, f"{project}.egg-link")
        self.site_packages_egglink = os.path.join(
            self.site_packages,
            f"{project}.egg-link",
        )

        # patches
        from pip._internal.utils import egg_link as utils

        self.old_site_packages = utils.site_packages
        self.mock_site_packages = utils.site_packages = "SITE_PACKAGES"
        self.old_running_under_virtualenv = utils.running_under_virtualenv
        self.mock_running_under_virtualenv = utils.running_under_virtualenv = Mock()
        self.old_virtualenv_no_global = utils.virtualenv_no_global
        self.mock_virtualenv_no_global = utils.virtualenv_no_global = Mock()
        self.old_user_site = utils.user_site
        self.mock_user_site = utils.user_site = self.user_site
        from os import path

        self.old_isfile = path.isfile
        self.mock_isfile = path.isfile = Mock()

    def teardown_method(self) -> None:
        from pip._internal.utils import egg_link as utils

        utils.site_packages = self.old_site_packages
        utils.running_under_virtualenv = self.old_running_under_virtualenv
        utils.virtualenv_no_global = self.old_virtualenv_no_global
        utils.user_site = self.old_user_site
        from os import path

        path.isfile = self.old_isfile

    def eggLinkInUserSite(self, egglink: str) -> bool:
        return egglink == self.user_site_egglink

    def eggLinkInSitePackages(self, egglink: str) -> bool:
        return egglink == self.site_packages_egglink

    # ####################### #
    # # egglink in usersite # #
    # ####################### #
    def test_egglink_in_usersite_notvenv(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.user_site_egglink
        )

    def test_egglink_in_usersite_venv_noglobal(self) -> None:
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path_from_location(self.mock_dist.project_name) is None

    def test_egglink_in_usersite_venv_global(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.user_site_egglink
        )

    # ####################### #
    # # egglink in sitepkgs # #
    # ####################### #
    def test_egglink_in_sitepkgs_notvenv(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.site_packages_egglink
        )

    def test_egglink_in_sitepkgs_venv_noglobal(self) -> None:
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.site_packages_egglink
        )

    def test_egglink_in_sitepkgs_venv_global(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.site_packages_egglink
        )

    # ################################## #
    # # egglink in usersite & sitepkgs # #
    # ################################## #
    def test_egglink_in_both_notvenv(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = True
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.user_site_egglink
        )

    def test_egglink_in_both_venv_noglobal(self) -> None:
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.site_packages_egglink
        )

    def test_egglink_in_both_venv_global(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert (
            egg_link_path_from_location(self.mock_dist.project_name)
            == self.site_packages_egglink
        )

    # ############## #
    # # no egglink # #
    # ############## #
    def test_noegglink_in_sitepkgs_notvenv(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = False
        assert egg_link_path_from_location(self.mock_dist.project_name) is None

    def test_noegglink_in_sitepkgs_venv_noglobal(self) -> None:
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path_from_location(self.mock_dist.project_name) is None

    def test_noegglink_in_sitepkgs_venv_global(self) -> None:
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path_from_location(self.mock_dist.project_name) is None


def test_rmtree_errorhandler_nonexistent_directory(tmpdir: Path) -> None:
    """
    Test rmtree_errorhandler ignores the given non-existing directory.
    """
    nonexistent_path = str(tmpdir / "foo")
    mock_func = Mock()
    # Argument 3 to "rmtree_errorhandler" has incompatible type "None"; expected
    # "Tuple[Type[BaseException], BaseException, TracebackType]"
    rmtree_errorhandler(mock_func, nonexistent_path, None)  # type: ignore[arg-type]
    mock_func.assert_not_called()


def test_rmtree_errorhandler_readonly_directory(tmpdir: Path) -> None:
    """
    Test rmtree_errorhandler makes the given read-only directory writable.
    """
    # Create read only directory
    subdir_path = tmpdir / "subdir"
    subdir_path.mkdir()
    path = str(subdir_path)
    os.chmod(path, stat.S_IREAD)

    # Make sure mock_func is called with the given path
    mock_func = Mock()
    # Argument 3 to "rmtree_errorhandler" has incompatible type "None"; expected
    # "Tuple[Type[BaseException], BaseException, TracebackType]"
    rmtree_errorhandler(mock_func, path, None)  # type: ignore[arg-type]
    mock_func.assert_called_with(path)

    # Make sure the path is now writable
    assert os.stat(path).st_mode & stat.S_IWRITE


def test_rmtree_errorhandler_reraises_error(tmpdir: Path) -> None:
    """
    Test rmtree_errorhandler reraises an exception
    by the given unreadable directory.
    """
    # Create directory without read permission
    path = tmpdir / "subdir"
    path.mkdir()
    old_mode = path.stat().st_mode
    path.chmod(stat.S_IWRITE)

    mock_func = Mock()

    try:
        raise RuntimeError("test message")
    except RuntimeError:
        # Make sure the handler reraises an exception
        with pytest.raises(RuntimeError, match="test message"):
            # Argument 3 to "rmtree_errorhandler" has incompatible type
            # "Union[Tuple[Type[BaseException], BaseException, TracebackType],
            # Tuple[None, None, None]]"; expected "Tuple[Type[BaseException],
            # BaseException, TracebackType]"
            rmtree_errorhandler(
                mock_func, path, sys.exc_info()  # type: ignore[arg-type]
            )
    finally:
        # Restore permissions to let pytest to clean up temp dirs
        path.chmod(old_mode)

    mock_func.assert_not_called()


def test_rmtree_skips_nonexistent_directory() -> None:
    """
    Test wrapped rmtree doesn't raise an error
    by the given nonexistent directory.
    """
    rmtree.__wrapped__("nonexistent-subdir")  # type: ignore[attr-defined]


class Failer:
    def __init__(self, duration: int = 1) -> None:
        self.succeed_after = time.time() + duration

    def call(self, *args: Any, **kw: Any) -> None:
        """Fail with OSError self.max_fails times"""
        if time.time() < self.succeed_after:
            raise OSError("Failed")


def test_rmtree_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test pip._internal.utils.rmtree will retry failures
    """
    monkeypatch.setattr(shutil, "rmtree", Failer(duration=1).call)
    rmtree("foo")


def test_rmtree_retries_for_3sec(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test pip._internal.utils.rmtree will retry failures for no more than 3 sec
    """
    monkeypatch.setattr(shutil, "rmtree", Failer(duration=5).call)
    with pytest.raises(OSError):
        rmtree("foo")


if sys.byteorder == "little":
    expected_byte_string = (
        "b'\\xff\\xfe/\\x00p\\x00a\\x00t\\x00h\\x00/\\x00d\\x00\\xe9\\x00f\\x00'"
    )
elif sys.byteorder == "big":
    expected_byte_string = (
        "b'\\xfe\\xff\\x00/\\x00p\\x00a\\x00t\\x00h\\x00/\\x00d\\x00\\xe9\\x00f'"
    )


class Test_normalize_path:
    # Technically, symlinks are possible on Windows, but you need a special
    # permission bit to create them, and Python 2 doesn't support it anyway, so
    # it's easiest just to skip this test on Windows altogether.
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_resolve_symlinks(self, tmpdir: Path) -> None:
        print(type(tmpdir))
        print(dir(tmpdir))
        orig_working_dir = os.getcwd()
        os.chdir(tmpdir)
        try:
            d = os.path.join("foo", "bar")
            f = os.path.join(d, "file1")
            os.makedirs(d)
            with open(f, "w"):  # Create the file
                pass

            os.symlink(d, "dir_link")
            os.symlink(f, "file_link")

            assert normalize_path(
                "dir_link/file1", resolve_symlinks=True
            ) == os.path.join(tmpdir, f)
            assert normalize_path(
                "dir_link/file1", resolve_symlinks=False
            ) == os.path.join(tmpdir, "dir_link", "file1")

            assert normalize_path("file_link", resolve_symlinks=True) == os.path.join(
                tmpdir, f
            )
            assert normalize_path("file_link", resolve_symlinks=False) == os.path.join(
                tmpdir, "file_link"
            )
        finally:
            os.chdir(orig_working_dir)


class TestHashes:
    """Tests for pip._internal.utils.hashes"""

    @pytest.mark.parametrize(
        "hash_name, hex_digest, expected",
        [
            # Test a value that matches but with the wrong hash_name.
            ("sha384", 128 * "a", False),
            # Test matching values, including values other than the first.
            ("sha512", 128 * "a", True),
            ("sha512", 128 * "b", True),
            # Test a matching hash_name with a value that doesn't match.
            ("sha512", 128 * "c", False),
        ],
    )
    def test_is_hash_allowed(
        self, hash_name: str, hex_digest: str, expected: bool
    ) -> None:
        hashes_data = {
            "sha512": [128 * "a", 128 * "b"],
        }
        hashes = Hashes(hashes_data)
        assert hashes.is_hash_allowed(hash_name, hex_digest) == expected

    def test_success(self, tmpdir: Path) -> None:
        """Make sure no error is raised when at least one hash matches.

        Test check_against_path because it calls everything else.

        """
        file = tmpdir / "to_hash"
        file.write_text("hello")
        hashes = Hashes(
            {
                "sha256": [
                    "2cf24dba5fb0a30e26e83b2ac5b9e29e"
                    "1b161e5c1fa7425e73043362938b9824"
                ],
                "sha224": ["wrongwrong"],
                "md5": ["5d41402abc4b2a76b9719d911017c592"],
            }
        )
        hashes.check_against_path(os.fspath(file))

    def test_failure(self) -> None:
        """Hashes should raise HashMismatch when no hashes match."""
        hashes = Hashes({"sha256": ["wrongwrong"]})
        with pytest.raises(HashMismatch):
            hashes.check_against_file(BytesIO(b"hello"))

    def test_missing_hashes(self) -> None:
        """MissingHashes should raise HashMissing when any check is done."""
        with pytest.raises(HashMissing):
            MissingHashes().check_against_file(BytesIO(b"hello"))

    def test_unknown_hash(self) -> None:
        """Hashes should raise InstallationError when it encounters an unknown
        hash."""
        hashes = Hashes({"badbad": ["dummy"]})
        with pytest.raises(InstallationError):
            hashes.check_against_file(BytesIO(b"hello"))

    def test_non_zero(self) -> None:
        """Test that truthiness tests tell whether any known-good hashes
        exist."""
        assert Hashes({"sha256": ["dummy"]})
        assert not Hashes()
        assert not Hashes({})

    def test_equality(self) -> None:
        assert Hashes() == Hashes()
        assert Hashes({"sha256": ["abcd"]}) == Hashes({"sha256": ["abcd"]})
        assert Hashes({"sha256": ["ab", "cd"]}) == Hashes({"sha256": ["cd", "ab"]})

    def test_hash(self) -> None:
        cache = {}
        cache[Hashes({"sha256": ["ab", "cd"]})] = 42
        assert cache[Hashes({"sha256": ["ab", "cd"]})] == 42

    def test_has_one_of(self) -> None:
        hashes = Hashes({"sha256": ["abcd", "efgh"], "sha384": ["ijkl"]})
        assert hashes.has_one_of({"sha256": "abcd"})
        assert hashes.has_one_of({"sha256": "efgh"})
        assert not hashes.has_one_of({"sha256": "xyzt"})
        empty_hashes = Hashes()
        assert not empty_hashes.has_one_of({"sha256": "xyzt"})


def raises(error: Type[Exception]) -> NoReturn:
    raise error


class TestGlibc:
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_glibc_version_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            os,
            "confstr",
            lambda x: "glibc 2.20",
            raising=False,
        )
        assert glibc_version_string() == "2.20"

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_glibc_version_string_confstr(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            os,
            "confstr",
            lambda x: "glibc 2.20",
            raising=False,
        )
        assert glibc_version_string_confstr() == "2.20"

    @pytest.mark.parametrize(
        "failure",
        [
            lambda x: raises(ValueError),
            lambda x: raises(OSError),
            lambda x: "XXX",
        ],
    )
    def test_glibc_version_string_confstr_fail(
        self, monkeypatch: pytest.MonkeyPatch, failure: Callable[[Any], Any]
    ) -> None:
        monkeypatch.setattr(os, "confstr", failure, raising=False)
        assert glibc_version_string_confstr() is None

    def test_glibc_version_string_confstr_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(os, "confstr", raising=False)
        assert glibc_version_string_confstr() is None

    def test_glibc_version_string_ctypes_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "ctypes", None)
        assert glibc_version_string_ctypes() is None


@pytest.mark.parametrize(
    "version_info, expected",
    [
        ((), (0, 0, 0)),
        ((3,), (3, 0, 0)),
        ((3, 6), (3, 6, 0)),
        ((3, 6, 2), (3, 6, 2)),
        ((3, 6, 2, 4), (3, 6, 2)),
    ],
)
def test_normalize_version_info(
    version_info: Tuple[int, ...], expected: Tuple[int, int, int]
) -> None:
    actual = normalize_version_info(version_info)
    assert actual == expected


class TestGetProg:
    @pytest.mark.parametrize(
        "argv, executable, expected",
        [
            ("/usr/bin/pip", "", "pip"),
            ("-c", "/usr/bin/python", "/usr/bin/python -m pip"),
            ("__main__.py", "/usr/bin/python", "/usr/bin/python -m pip"),
            ("/usr/bin/pip3", "", "pip3"),
        ],
    )
    def test_get_prog(
        self, monkeypatch: pytest.MonkeyPatch, argv: str, executable: str, expected: str
    ) -> None:
        monkeypatch.setattr("pip._internal.utils.misc.sys.argv", [argv])
        monkeypatch.setattr("pip._internal.utils.misc.sys.executable", executable)
        assert get_prog() == expected


@pytest.mark.parametrize(
    "host_port, expected_netloc",
    [
        # Test domain name.
        (("example.com", None), "example.com"),
        (("example.com", 5000), "example.com:5000"),
        # Test IPv4 address.
        (("127.0.0.1", None), "127.0.0.1"),
        (("127.0.0.1", 5000), "127.0.0.1:5000"),
        # Test bare IPv6 address.
        (("2001:db6::1", None), "2001:db6::1"),
        # Test IPv6 with port.
        (("2001:db6::1", 5000), "[2001:db6::1]:5000"),
    ],
)
def test_build_netloc(
    host_port: Tuple[str, Optional[int]], expected_netloc: str
) -> None:
    assert build_netloc(*host_port) == expected_netloc


@pytest.mark.parametrize(
    "netloc, expected_url, expected_host_port",
    [
        # Test domain name.
        ("example.com", "https://example.com", ("example.com", None)),
        ("example.com:5000", "https://example.com:5000", ("example.com", 5000)),
        # Test IPv4 address.
        ("127.0.0.1", "https://127.0.0.1", ("127.0.0.1", None)),
        ("127.0.0.1:5000", "https://127.0.0.1:5000", ("127.0.0.1", 5000)),
        # Test bare IPv6 address.
        ("2001:db6::1", "https://[2001:db6::1]", ("2001:db6::1", None)),
        # Test IPv6 with port.
        ("[2001:db6::1]:5000", "https://[2001:db6::1]:5000", ("2001:db6::1", 5000)),
        # Test netloc with auth.
        (
            "user:password@localhost:5000",
            "https://user:password@localhost:5000",
            ("localhost", 5000),
        ),
    ],
)
def test_build_url_from_netloc_and_parse_netloc(
    netloc: str,
    expected_url: str,
    expected_host_port: Tuple[str, Optional[int]],
) -> None:
    assert build_url_from_netloc(netloc) == expected_url
    assert parse_netloc(netloc) == expected_host_port


@pytest.mark.parametrize(
    "netloc, expected",
    [
        # Test a basic case.
        ("example.com", ("example.com", (None, None))),
        # Test with username and no password.
        ("user@example.com", ("example.com", ("user", None))),
        # Test with username and password.
        ("user:pass@example.com", ("example.com", ("user", "pass"))),
        # Test with username and empty password.
        ("user:@example.com", ("example.com", ("user", ""))),
        # Test the password containing an @ symbol.
        ("user:pass@word@example.com", ("example.com", ("user", "pass@word"))),
        # Test the password containing a : symbol.
        ("user:pass:word@example.com", ("example.com", ("user", "pass:word"))),
        # Test URL-encoded reserved characters.
        ("user%3Aname:%23%40%5E@example.com", ("example.com", ("user:name", "#@^"))),
    ],
)
def test_split_auth_from_netloc(
    netloc: str, expected: Tuple[str, Tuple[Optional[str], Optional[str]]]
) -> None:
    actual = split_auth_from_netloc(netloc)
    assert actual == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        # Test a basic case.
        (
            "http://example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", (None, None)),
        ),
        # Test with username and no password.
        (
            "http://user@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user", None)),
        ),
        # Test with username and password.
        (
            "http://user:pass@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user", "pass")),
        ),
        # Test with username and empty password.
        (
            "http://user:@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user", "")),
        ),
        # Test the password containing an @ symbol.
        (
            "http://user:pass@word@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user", "pass@word")),
        ),
        # Test the password containing a : symbol.
        (
            "http://user:pass:word@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user", "pass:word")),
        ),
        # Test URL-encoded reserved characters.
        (
            "http://user%3Aname:%23%40%5E@example.com/path#anchor",
            ("http://example.com/path#anchor", "example.com", ("user:name", "#@^")),
        ),
    ],
)
def test_split_auth_netloc_from_url(
    url: str, expected: Tuple[str, str, Tuple[Optional[str], Optional[str]]]
) -> None:
    actual = split_auth_netloc_from_url(url)
    assert actual == expected


@pytest.mark.parametrize(
    "netloc, expected",
    [
        # Test a basic case.
        ("example.com", "example.com"),
        # Test with username and no password.
        ("accesstoken@example.com", "****@example.com"),
        # Test with username and password.
        ("user:pass@example.com", "user:****@example.com"),
        # Test with username and empty password.
        ("user:@example.com", "user:****@example.com"),
        # Test the password containing an @ symbol.
        ("user:pass@word@example.com", "user:****@example.com"),
        # Test the password containing a : symbol.
        ("user:pass:word@example.com", "user:****@example.com"),
        # Test URL-encoded reserved characters.
        ("user%3Aname:%23%40%5E@example.com", "user%3Aname:****@example.com"),
    ],
)
def test_redact_netloc(netloc: str, expected: str) -> None:
    actual = redact_netloc(netloc)
    assert actual == expected


@pytest.mark.parametrize(
    "auth_url, expected_url",
    [
        (
            "https://user:pass@domain.tld/project/tags/v0.2",
            "https://domain.tld/project/tags/v0.2",
        ),
        (
            "https://domain.tld/project/tags/v0.2",
            "https://domain.tld/project/tags/v0.2",
        ),
        (
            "https://user:pass@domain.tld/svn/project/trunk@8181",
            "https://domain.tld/svn/project/trunk@8181",
        ),
        (
            "https://domain.tld/project/trunk@8181",
            "https://domain.tld/project/trunk@8181",
        ),
        ("git+https://pypi.org/something", "git+https://pypi.org/something"),
        ("git+https://user:pass@pypi.org/something", "git+https://pypi.org/something"),
        ("git+ssh://git@pypi.org/something", "git+ssh://pypi.org/something"),
    ],
)
def test_remove_auth_from_url(auth_url: str, expected_url: str) -> None:
    url = remove_auth_from_url(auth_url)
    assert url == expected_url


@pytest.mark.parametrize(
    "auth_url, expected_url",
    [
        ("https://accesstoken@example.com/abc", "https://****@example.com/abc"),
        ("https://user:password@example.com", "https://user:****@example.com"),
        ("https://user:@example.com", "https://user:****@example.com"),
        ("https://example.com", "https://example.com"),
        # Test URL-encoded reserved characters.
        (
            "https://user%3Aname:%23%40%5E@example.com",
            "https://user%3Aname:****@example.com",
        ),
    ],
)
def test_redact_auth_from_url(auth_url: str, expected_url: str) -> None:
    url = redact_auth_from_url(auth_url)
    assert url == expected_url


@pytest.mark.parametrize(
    "req, expected",
    [
        ("pkga", "pkga"),
        (
            "resolvelib@ "
            " git+https://test-user:test-pass@github.com/sarugaku/resolvelib@1.0.1",
            "resolvelib@"
            " git+https://test-user:****@github.com/sarugaku/resolvelib@1.0.1",
        ),
        (
            "resolvelib@"
            " git+https://test-user:test-pass@github.com/sarugaku/resolvelib@1.0.1"
            " ; python_version>='3.6'",
            "resolvelib@"
            " git+https://test-user:****@github.com/sarugaku/resolvelib@1.0.1"
            ' ; python_version >= "3.6"',
        ),
    ],
)
def test_redact_auth_from_requirement(req: str, expected: str) -> None:
    assert redact_auth_from_requirement(Requirement(req)) == expected


class TestHiddenText:
    def test_basic(self) -> None:
        """
        Test str(), repr(), and attribute access.
        """
        hidden = HiddenText("my-secret", redacted="######")
        assert repr(hidden) == "<HiddenText '######'>"
        assert str(hidden) == "######"
        assert hidden.redacted == "######"
        assert hidden.secret == "my-secret"

    def test_equality_with_str(self) -> None:
        """
        Test equality (and inequality) with str objects.
        """
        hidden = HiddenText("secret", redacted="****")

        # Test that the object doesn't compare equal to either its original
        # or redacted forms.
        assert hidden != hidden.secret
        assert hidden.secret != hidden

        assert hidden != hidden.redacted
        assert hidden.redacted != hidden

    def test_equality_same_secret(self) -> None:
        """
        Test equality with an object having the same secret.
        """
        # Choose different redactions for the two objects.
        hidden1 = HiddenText("secret", redacted="****")
        hidden2 = HiddenText("secret", redacted="####")

        assert hidden1 == hidden2
        # Also test __ne__.
        assert not hidden1 != hidden2

    def test_equality_different_secret(self) -> None:
        """
        Test equality with an object having a different secret.
        """
        hidden1 = HiddenText("secret-1", redacted="****")
        hidden2 = HiddenText("secret-2", redacted="****")

        assert hidden1 != hidden2
        # Also test __eq__.
        assert not hidden1 == hidden2


def test_hide_value() -> None:
    hidden = hide_value("my-secret")
    assert repr(hidden) == "<HiddenText '****'>"
    assert str(hidden) == "****"
    assert hidden.redacted == "****"
    assert hidden.secret == "my-secret"


def test_hide_url() -> None:
    hidden_url = hide_url("https://user:password@example.com")
    assert repr(hidden_url) == "<HiddenText 'https://user:****@example.com'>"
    assert str(hidden_url) == "https://user:****@example.com"
    assert hidden_url.redacted == "https://user:****@example.com"
    assert hidden_url.secret == "https://user:password@example.com"


@pytest.fixture
def patch_deprecation_check_version() -> Iterator[None]:
    # We do this, so that the deprecation tests are easier to write.
    import pip._internal.utils.deprecation as d

    old_version = d.current_version
    d.current_version = "1.0"
    yield
    d.current_version = old_version


@pytest.mark.usefixtures("patch_deprecation_check_version")
@pytest.mark.parametrize("replacement", [None, "a magic 8 ball"])
@pytest.mark.parametrize("gone_in", [None, "2.0"])
@pytest.mark.parametrize("issue", [None, 988])
@pytest.mark.parametrize("feature_flag", [None, "magic-8-ball"])
def test_deprecated_message_contains_information(
    gone_in: Optional[str],
    replacement: Optional[str],
    issue: Optional[int],
    feature_flag: Optional[str],
) -> None:
    with pytest.warns(PipDeprecationWarning) as record:
        deprecated(
            reason="Stop doing this!",
            replacement=replacement,
            gone_in=gone_in,
            feature_flag=feature_flag,
            issue=issue,
        )

    assert len(record) == 1
    assert isinstance(record[0].message, PipDeprecationWarning)
    message = record[0].message.args[0]

    assert "DEPRECATION: Stop doing this!" in message
    # Ensure non-None values are mentioned.
    for item in [gone_in, replacement, issue, feature_flag]:
        if item is not None:
            assert str(item) in message


@pytest.mark.usefixtures("patch_deprecation_check_version")
@pytest.mark.parametrize("replacement", [None, "a magic 8 ball"])
@pytest.mark.parametrize("issue", [None, 988])
@pytest.mark.parametrize("feature_flag", [None, "magic-8-ball"])
def test_deprecated_raises_error_if_too_old(
    replacement: Optional[str], issue: Optional[int], feature_flag: Optional[str]
) -> None:
    with pytest.raises(PipDeprecationWarning) as exception:
        deprecated(
            reason="Stop doing this!",
            gone_in="1.0",  # this matches the patched version.
            replacement=replacement,
            feature_flag=feature_flag,
            issue=issue,
        )

    message = exception.value.args[0]

    assert "DEPRECATION: Stop doing this!" in message
    assert "1.0" in message
    assert str(feature_flag) not in message
    # Ensure non-None values are mentioned.
    for item in [replacement, issue]:
        if item is not None:
            assert str(item) in message


@pytest.mark.usefixtures("patch_deprecation_check_version")
def test_deprecated_message_reads_well_past() -> None:
    with pytest.raises(PipDeprecationWarning) as exception:
        deprecated(
            reason="Stop doing this!",
            gone_in="1.0",  # this matches the patched version.
            replacement="to be nicer",
            feature_flag="magic-8-ball",
            issue=100000,
        )

    message = exception.value.args[0]

    assert message == (
        "DEPRECATION: Stop doing this! "
        "Since pip 1.0, this is no longer supported. "
        "A possible replacement is to be nicer. "
        "Discussion can be found at https://github.com/pypa/pip/issues/100000"
    )


@pytest.mark.usefixtures("patch_deprecation_check_version")
def test_deprecated_message_reads_well_future() -> None:
    with pytest.warns(PipDeprecationWarning) as record:
        deprecated(
            reason="Stop doing this!",
            gone_in="2.0",  # this is greater than the patched version.
            replacement="to be nicer",
            feature_flag="crisis",
            issue=100000,
        )

    assert len(record) == 1
    assert isinstance(record[0].message, PipDeprecationWarning)
    message = record[0].message.args[0]

    assert message == (
        "DEPRECATION: Stop doing this! "
        "pip 2.0 will enforce this behaviour change. "
        "A possible replacement is to be nicer. "
        "You can use the flag --use-feature=crisis to test the upcoming behaviour. "
        "Discussion can be found at https://github.com/pypa/pip/issues/100000"
    )


def test_make_setuptools_shim_args() -> None:
    # Test all arguments at once, including the overall ordering.
    args = make_setuptools_shim_args(
        "/dir/path/setup.py",
        global_options=["--some", "--option"],
        no_user_config=True,
        unbuffered_output=True,
    )

    assert args[1:3] == ["-u", "-c"]
    assert args[4:] == ["--some", "--option", "--no-user-cfg"]

    shim = args[3]
    # Spot-check key aspects of the command string.
    assert "import setuptools" in shim
    assert "'/dir/path/setup.py'" in args[3]
    assert "sys.argv[0] = __file__" in args[3]


@pytest.mark.parametrize("global_options", [None, [], ["--some", "--option"]])
def test_make_setuptools_shim_args__global_options(
    global_options: Optional[List[str]],
) -> None:
    args = make_setuptools_shim_args(
        "/dir/path/setup.py",
        global_options=global_options,
    )

    if global_options:
        assert len(args) == 5
        for option in global_options:
            assert option in args
    else:
        assert len(args) == 3


@pytest.mark.parametrize("no_user_config", [False, True])
def test_make_setuptools_shim_args__no_user_config(no_user_config: bool) -> None:
    args = make_setuptools_shim_args(
        "/dir/path/setup.py",
        no_user_config=no_user_config,
    )
    assert ("--no-user-cfg" in args) == no_user_config


@pytest.mark.parametrize("unbuffered_output", [False, True])
def test_make_setuptools_shim_args__unbuffered_output(unbuffered_output: bool) -> None:
    args = make_setuptools_shim_args(
        "/dir/path/setup.py", unbuffered_output=unbuffered_output
    )
    assert ("-u" in args) == unbuffered_output


@pytest.mark.parametrize(
    "isatty,no_stdin,expected",
    [
        (True, False, True),
        (False, False, False),
        (True, True, False),
        (False, True, False),
    ],
)
def test_is_console_interactive(
    monkeypatch: pytest.MonkeyPatch, isatty: bool, no_stdin: bool, expected: bool
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", Mock(return_value=isatty))

    if no_stdin:
        monkeypatch.setattr(sys, "stdin", None)

    assert is_console_interactive() is expected


@pytest.mark.parametrize(
    "size,expected",
    [
        (123, "123 bytes"),
        (1234, "1.2 kB"),
        (123456, "123 kB"),
        (1234567890, "1234.6 MB"),
    ],
)
def test_format_size(size: int, expected: str) -> None:
    assert format_size(size) == expected


@pytest.mark.parametrize(
    "rows, table, sizes",
    [
        ([], [], []),
        (
            [
                ("I?", "version", "sdist", "wheel"),
                ("", "1.18.2", "zip", "cp38-cp38m-win_amd64"),
                ("v", 1.18, "zip"),
            ],
            [
                "I? version sdist wheel",
                "   1.18.2  zip   cp38-cp38m-win_amd64",
                "v  1.18    zip",
            ],
            [2, 7, 5, 20],
        ),
        (
            [("I?", "version", "sdist", "wheel"), (), ("v", "1.18.1", "zip")],
            ["I? version sdist wheel", "", "v  1.18.1  zip"],
            [2, 7, 5, 5],
        ),
    ],
)
def test_tabulate(rows: List[Tuple[str]], table: List[str], sizes: List[int]) -> None:
    assert tabulate(rows) == (table, sizes)
