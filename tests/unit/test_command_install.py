import errno

import pytest
from mock import patch
from pip._vendor.packaging.requirements import Requirement

from pip._internal.commands.install import (
    create_env_error_message,
    decide_user_install,
    reject_location_related_install_options,
)
from pip._internal.exceptions import CommandError
from pip._internal.req.req_install import InstallRequirement


class TestDecideUserInstall:
    @patch('site.ENABLE_USER_SITE', True)
    @patch('pip._internal.commands.install.site_packages_writable')
    def test_prefix_and_target(self, sp_writable):
        sp_writable.return_value = False

        assert decide_user_install(
            use_user_site=None, prefix_path='foo'
        ) is False

        assert decide_user_install(
            use_user_site=None, target_dir='bar'
        ) is False

    @pytest.mark.parametrize(
        "enable_user_site,site_packages_writable,result", [
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, False),
        ])
    def test_most_cases(
        self, enable_user_site, site_packages_writable, result, monkeypatch,
    ):
        monkeypatch.setattr('site.ENABLE_USER_SITE', enable_user_site)
        monkeypatch.setattr(
            'pip._internal.commands.install.site_packages_writable',
            lambda **kw: site_packages_writable
        )
        assert decide_user_install(use_user_site=None) is result


def test_rejection_for_pip_install_options():
    install_options = ["--prefix=/hello"]
    with pytest.raises(CommandError) as e:
        reject_location_related_install_options([], install_options)

    assert "['--prefix'] from command line" in str(e.value)


def test_rejection_for_location_requirement_options():
    install_options = []

    bad_named_req_options = ["--home=/wow"]
    bad_named_req = InstallRequirement(
        Requirement("hello"), "requirements.txt",
        install_options=bad_named_req_options
    )

    bad_unnamed_req_options = ["--install-lib=/lib"]
    bad_unnamed_req = InstallRequirement(
        None, "requirements2.txt", install_options=bad_unnamed_req_options
    )

    with pytest.raises(CommandError) as e:
        reject_location_related_install_options(
            [bad_named_req, bad_unnamed_req], install_options
        )

    assert (
        "['--install-lib'] from <InstallRequirement> (from requirements2.txt)"
        in str(e.value)
    )
    assert "['--home'] from hello (from requirements.txt)" in str(e.value)


@pytest.mark.parametrize('error, show_traceback, using_user_site, expected', [
    # show_traceback = True, using_user_site = True
    (EnvironmentError("Illegal byte sequence"), True, True, 'Could not install'
        ' packages due to an EnvironmentError.\n'),
    (EnvironmentError(errno.EACCES, "No file permission"), True, True, 'Could'
        ' not install packages due to an EnvironmentError.\nCheck the'
        ' permissions.\n'),
    # show_traceback = True, using_user_site = False
    (EnvironmentError("Illegal byte sequence"), True, False, 'Could not'
        ' install packages due to an EnvironmentError.\n'),
    (EnvironmentError(errno.EACCES, "No file permission"), True, False, 'Could'
        ' not install packages due to an EnvironmentError.\nConsider using the'
        ' `--user` option or check the permissions.\n'),
    # show_traceback = False, using_user_site = True
    (EnvironmentError("Illegal byte sequence"), False, True, 'Could not'
        ' install packages due to an EnvironmentError: Illegal byte'
        ' sequence\n'),
    (EnvironmentError(errno.EACCES, "No file permission"), False, True, 'Could'
        ' not install packages due to an EnvironmentError: [Errno 13] No file'
        ' permission\nCheck the permissions.\n'),
    # show_traceback = False, using_user_site = False
    (EnvironmentError("Illegal byte sequence"), False, False, 'Could not'
        ' install packages due to an EnvironmentError: Illegal byte sequence'
        '\n'),
    (EnvironmentError(errno.EACCES, "No file permission"), False, False,
        'Could not install packages due to an EnvironmentError: [Errno 13] No'
        ' file permission\nConsider using the `--user` option or check the'
        ' permissions.\n'),
])
def test_create_env_error_message(
    error, show_traceback, using_user_site, expected
):
    msg = create_env_error_message(error, show_traceback, using_user_site)
    assert msg == expected
