"""Test user site-packages installation decision
and other install destination option conflicts.
"""

from itertools import product

from pytest import fixture, mark, param, raises

from pip._internal.commands.install import decide_user_install
from pip._internal.exceptions import CommandError, InstallationError

ENABLE_USER_SITE = 'pip._internal.commands.install.ENABLE_USER_SITE'
ISDIR = 'pip._internal.commands.install.os.path.isdir'
EXISTS = 'pip._internal.commands.install.os.path.exists'
SITE_WRITABLE = 'pip._internal.commands.install.site_packages_writable'
WRITABLE = 'pip._internal.commands.install.test_writable_dir'
VIRTUALENV_NO_GLOBAL = 'pip._internal.commands.install.virtualenv_no_global'


def false(*args, **kwargs):
    """Return False."""
    return False


def true(*args, **kwargs):
    """Return True."""
    return True


@fixture
def user_site_enabled(monkeypatch):
    """site.ENABLE_USER_SITE mocked to be True."""
    monkeypatch.setattr(ENABLE_USER_SITE, True)


@fixture
def nonexists(monkeypatch):
    """os.path.exists mocked to always return False."""
    monkeypatch.setattr(EXISTS, false)


@fixture
def exists(monkeypatch):
    """os.path.exists mocked to always return True."""
    monkeypatch.setattr(EXISTS, true)


@fixture
def isnotdir(monkeypatch):
    """os.path.isdir mocked to always return False."""
    monkeypatch.setattr(ISDIR, false)


@fixture
def nonwritable(monkeypatch):
    """test_writable_dir mocked to always return False."""
    monkeypatch.setattr(WRITABLE, false)


@fixture
def writable(monkeypatch):
    """test_writable_dir mocked to always return True."""
    monkeypatch.setattr(WRITABLE, true)


@fixture
def virtualenv_global(monkeypatch):
    """virtualenv_no_global mocked to always return False."""
    monkeypatch.setattr(VIRTUALENV_NO_GLOBAL, false)


@fixture
def virtualenv_no_global(monkeypatch):
    """virtualenv_no_global mocked to always return False."""
    monkeypatch.setattr(VIRTUALENV_NO_GLOBAL, true)


@mark.parametrize(('use_user_site', 'prefix_path', 'target_dir'),
                  filter(lambda args: sum(map(bool, args)) > 1,
                         product((False, True), (None, 'foo'), (None, 'bar'))))
def test_conflicts(use_user_site, prefix_path, target_dir):
    """Test conflicts of target, user, root and prefix options."""
    with raises(CommandError):
        decide_user_install(use_user_site=use_user_site,
                            prefix_path=prefix_path,
                            target_dir=target_dir)


def test_target_exists_error(writable, exists, isnotdir):
    """Test existing target which is not a directory."""
    with raises(InstallationError):
        decide_user_install(target_dir='bar')


@mark.parametrize(('exist', 'is_dir'),
                  ((false, false), (false, true), (true, true)))
def test_target_exists(exist, is_dir, writable, monkeypatch):
    """Test target paths for non-error exist-isdir combinations."""
    monkeypatch.setattr(EXISTS, exist)
    monkeypatch.setattr(ISDIR, is_dir)
    assert decide_user_install(target_dir='bar') is False


def test_target_nonwritable(nonexists, nonwritable):
    """Test nonwritable path check with target specified."""
    with raises(InstallationError):
        decide_user_install(target_dir='bar')


def test_target_writable(nonexists, writable):
    """Test writable path check with target specified."""
    assert decide_user_install(target_dir='bar') is False


def test_prefix_nonwritable(nonwritable):
    """Test nonwritable path check with prefix specified."""
    with raises(InstallationError):
        decide_user_install(prefix_path='foo')


def test_prefix_writable(writable):
    """Test writable path check with prefix specified."""
    assert decide_user_install(prefix_path='foo') is False


@mark.parametrize('kwargs', (
    param({'use_user_site': False}, id='not using user-site specified'),
    param({'root_path': 'baz'}, id='root path specified')))
def test_global_site_nonwritable(kwargs, nonwritable,
                                 virtualenv_global):
    """Test error handling when global site-packages is not writable."""
    with raises(InstallationError):
        decide_user_install(**kwargs)


@mark.parametrize('kwargs', (
    param({'use_user_site': True}, id='using user-site specified'),
    param({'root_path': 'baz'}, id='root path specified')))
def test_global_site_writable(kwargs, writable,
                              virtualenv_global, user_site_enabled):
    """Test if user site-packages decision is the same as specified
    when global site-packages is writable.
    """
    expected_decision = kwargs.get('use_user_site', False)
    assert decide_user_install(**kwargs) is expected_decision


@mark.parametrize('writable_global', (False, True))
def test_global_site_auto(writable_global, virtualenv_global,
                          user_site_enabled, monkeypatch):
    """Test error handling and user site-packages decision
    with writable and non-writable global site-packages,
    when no argument is provided.
    """
    monkeypatch.setattr(SITE_WRITABLE,
                        lambda **kwargs: kwargs.get('user') or writable_global)
    assert decide_user_install() is not writable_global


def test_enable_user_site_error(virtualenv_global, monkeypatch):
    """Test error raised when site.ENABLE_USER_SITE is None
    but use_user_site is requested.
    """
    monkeypatch.setattr(ENABLE_USER_SITE, None)
    with raises(InstallationError):
        decide_user_install(use_user_site=True)


@mark.parametrize(('use_user_site', 'enable_user_site'),
                  filter(lambda args: set(args) != {None, True},
                         product((None, False, True), (None, False, True))))
def test_enable_user_site(use_user_site, enable_user_site,
                          virtualenv_global, writable, monkeypatch):
    """Test with different values of site.ENABLE_USER_SITE."""
    monkeypatch.setattr(ENABLE_USER_SITE, enable_user_site)
    assert decide_user_install(use_user_site) is bool(use_user_site)


@mark.parametrize('use_user_site', (None, True))
def test_virtualenv_no_global(use_user_site, virtualenv_no_global,
                              user_site_enabled, nonwritable):
    """Test for final assertion of virtualenv_no_global
    when user site-packages is decided to be used.
    """
    with raises(InstallationError):
        decide_user_install(use_user_site)


def test_user_site_nonwritable(nonwritable):
    """Test when user-site is not writable,
    which usually only happens when root path is specified.
    """
    with raises(InstallationError):
        decide_user_install(True)
