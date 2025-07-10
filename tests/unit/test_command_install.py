import errno
from unittest import mock

import pytest

from pip._vendor.requests.exceptions import InvalidProxyURL

from pip._internal.commands import install
from pip._internal.commands.install import create_os_error_message, decide_user_install


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
