import errno
import sys
import warnings
from unittest import mock

import pytest

from pip._vendor.requests.exceptions import InvalidProxyURL

from pip._internal.commands import install
from pip._internal.commands.install import (
    _prevent_further_imports,
    create_os_error_message,
    decide_user_install,
)
from pip._internal.utils.deprecation import PipDeprecationWarning


class TestDecideUserInstall:
    @mock.patch("site.ENABLE_USER_SITE", True)
    @mock.patch("pip._internal.commands.install.site_packages_writable")
    def test_prefix_and_target(self, sp_writable: mock.Mock) -> None:
        sp_writable.return_value = False

        assert decide_user_install(use_user_site=None, prefix_path="foo") is False

        assert decide_user_install(use_user_site=None, target_dir="bar") is False

    @pytest.mark.parametrize(
        "enable_user_site,site_packages_writable,result",
        [
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_most_cases(
        self,
        enable_user_site: bool,
        site_packages_writable: bool,
        result: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("site.ENABLE_USER_SITE", enable_user_site)
        monkeypatch.setattr(
            "pip._internal.commands.install.site_packages_writable",
            lambda **kw: site_packages_writable,
        )
        assert decide_user_install(use_user_site=None) is result


@pytest.mark.parametrize(
    "error, show_traceback, using_user_site, expected",
    [
        # show_traceback = True, using_user_site = True
        (
            OSError("Illegal byte sequence"),
            True,
            True,
            "Could not install packages due to an OSError.\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            True,
            True,
            "Could"
            " not install packages due to an OSError.\nCheck the"
            " permissions.\n",
        ),
        # show_traceback = True, using_user_site = False
        (
            OSError("Illegal byte sequence"),
            True,
            False,
            "Could not install packages due to an OSError.\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            True,
            False,
            "Could"
            " not install packages due to an OSError.\nConsider using the"
            " `--user` option or check the permissions.\n",
        ),
        # show_traceback = False, using_user_site = True
        (
            OSError("Illegal byte sequence"),
            False,
            True,
            "Could not"
            " install packages due to an OSError: Illegal byte"
            " sequence\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            False,
            True,
            "Could"
            " not install packages due to an OSError: [Errno 13] No file"
            " permission\nCheck the permissions.\n",
        ),
        # show_traceback = False, using_user_site = False
        (
            OSError("Illegal byte sequence"),
            False,
            False,
            "Could not"
            " install packages due to an OSError: Illegal byte sequence"
            "\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            False,
            False,
            "Could not install packages due to an OSError: [Errno 13] No"
            " file permission\nConsider using the `--user` option or check the"
            " permissions.\n",
        ),
        # Testing custom InvalidProxyURL with help message
        #  show_traceback = True, using_user_site = True
        (
            InvalidProxyURL(),
            True,
            True,
            "Could not install packages due to an OSError.\n"
            "Consider checking your local proxy configuration"
            ' with "pip config debug".\n',
        ),
        # Testing both long path error (ENOENT)
        # and long file/folder name error (EINVAL) on Windows
        pytest.param(
            OSError(errno.ENOENT, "No such file or directory", f"C:{'/a'*261}"),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 2] No such file or directory: 'C:{'/a'*261}'\n"
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
        pytest.param(
            OSError(errno.EINVAL, "No such file or directory", f"C:/{'a'*256}"),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 22] No such file or directory: 'C:/{'a'*256}'\n"
            "HINT: This error might be caused by a file or folder name exceeding "
            "255 characters, which is a Windows limitation even if long paths "
            "are enabled.\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
        pytest.param(
            OSError(
                errno.EINVAL, "No such file or directory", f"C:{'/a'*261}/{'b'*256}"
            ),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 22] No such file or directory: 'C:{'/a' * 261}/{'b' * 256}'\n"
            "HINT: This error might be caused by a file or folder name exceeding "
            "255 characters, which is a Windows limitation even if long paths "
            "are enabled.\n "
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
    ],
)
def test_create_os_error_message(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
    show_traceback: bool,
    using_user_site: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(install, "running_under_virtualenv", lambda: False)
    msg = create_os_error_message(error, show_traceback, using_user_site)
    assert msg == expected


def test_prevent_further_imports_warns_on_import() -> None:
    """
    An import issued after _prevent_further_imports() has run must emit a
    deprecation warning via the registered audit hook, except when the
    imported module lives in the standard library.
    """
    captured_hooks: list[mock.Mock] = []

    with mock.patch.object(install, "_IMPORT_AUDIT_HOOK_INSTALLED", False):
        with mock.patch.object(sys, "addaudithook", side_effect=captured_hooks.append):
            _prevent_further_imports()

    assert len(captured_hooks) == 1, "Expected exactly one audit hook to be registered"
    audit_hook = captured_hooks[0]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        audit_hook("import", ("unknown_module",))

    assert len(caught) == 1
    assert "unknown_module" in str(caught[0].message)
    assert issubclass(caught[0].category, PipDeprecationWarning)

    # Standard library imports must not emit a warning: pip cannot shadow
    # them with a freshly installed distribution.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        audit_hook("import", ("os",))
        audit_hook("import", ("encodings.iso8859_15",))

    assert caught == []
