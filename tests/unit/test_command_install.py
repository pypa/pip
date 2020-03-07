import errno
from itertools import product

import pytest
from mock import patch
from pip._vendor.packaging.requirements import Requirement

from pip._internal.commands.install import (
    create_env_error_message,
    decide_user_install,
    reject_location_related_install_options,
)
from pip._internal.exceptions import CommandError, InstallationError
from pip._internal.req.req_install import InstallRequirement

ENABLE_USER_SITE = 'site.ENABLE_USER_SITE'
WRITABLE = 'pip._internal.commands.install.test_writable_dir'
ISDIR = 'pip._internal.commands.install.os.path.isdir'
EXISTS = 'pip._internal.commands.install.os.path.exists'


def false(*args, **kwargs):
    """Return False."""
    return False


def true(*args, **kwargs):
    """Return True."""
    return True


# virtualenv_no_global is tested by functional test
@patch('pip._internal.commands.install.virtualenv_no_global', false)
class TestDecideUserInstall:
    @pytest.mark.parametrize('use_user_site,prefix_path,target_dir,root_path',
                             filter(lambda args: sum(map(bool, args)) > 1,
                                    product((False, True), (None, 'foo'),
                                            (None, 'bar'), (None, 'baz'))))
    def test_conflicts(self, use_user_site,
                       prefix_path, target_dir, root_path):
        with pytest.raises(CommandError):
            decide_user_install(
                use_user_site=use_user_site, prefix_path=prefix_path,
                target_dir=target_dir, root_path=root_path)

    def test_target_dir(self):
        with patch(WRITABLE, true):
            with patch(EXISTS, true), patch(ISDIR, false):
                with pytest.raises(InstallationError):
                    decide_user_install(target_dir='bar')
            for exists, isdir in (false, false), (false, true), (true, true):
                with patch(EXISTS, exists), patch(ISDIR, isdir):
                    assert decide_user_install(target_dir='bar') is False

    def test_target_writable(self):
        with patch(EXISTS, false):
            with patch(WRITABLE, false), pytest.raises(InstallationError):
                decide_user_install(target_dir='bar')
            with patch(WRITABLE, true):
                assert decide_user_install(target_dir='bar') is False

    def test_prefix_writable(self):
        with patch(WRITABLE, false), pytest.raises(InstallationError):
            decide_user_install(prefix_path='foo')
        with patch(WRITABLE, true):
            assert decide_user_install(prefix_path='foo') is False

    def test_global_site_writable(self):
        with patch(ENABLE_USER_SITE, True):
            with patch(WRITABLE, false):
                with pytest.raises(InstallationError):
                    decide_user_install(use_user_site=False)
                with pytest.raises(InstallationError):
                    decide_user_install(root_path='baz')
                assert decide_user_install() is True
            with patch(WRITABLE, true):
                assert decide_user_install(use_user_site=True) is True
                assert decide_user_install(root_path='baz') is False
                assert decide_user_install() is False

    def test_enable_user_site(self):
        with patch(WRITABLE, true):
            with patch(ENABLE_USER_SITE, None):
                assert decide_user_install() is False
                assert decide_user_install(use_user_site=False) is False
                with pytest.raises(InstallationError):
                    decide_user_install(use_user_site=True)
            with patch(ENABLE_USER_SITE, False):
                assert decide_user_install() is False
                assert decide_user_install(use_user_site=False) is False
                assert decide_user_install(use_user_site=True) is True
            with patch(ENABLE_USER_SITE, True):
                assert decide_user_install(use_user_site=False) is False
                assert decide_user_install(use_user_site=True) is True
        with patch(WRITABLE, false), patch(ENABLE_USER_SITE, True):
            assert decide_user_install() is True


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
