import pytest
from mock import Mock
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.vcs import RevOptions, VersionControl
from pip._internal.vcs.bazaar import Bazaar
from pip._internal.vcs.git import Git, looks_like_hash
from pip._internal.vcs.mercurial import Mercurial
from pip._internal.vcs.subversion import Subversion
from tests.lib import pyversion

if pyversion >= '3':
    VERBOSE_FALSE = False
else:
    VERBOSE_FALSE = 0


def test_rev_options_repr():
    rev_options = RevOptions(Git(), 'develop')
    assert repr(rev_options) == "<RevOptions git: rev='develop'>"


@pytest.mark.parametrize(('vcs', 'expected1', 'expected2', 'kwargs'), [
    # First check VCS-specific RevOptions behavior.
    (Bazaar(), [], ['-r', '123'], {}),
    (Git(), ['HEAD'], ['123'], {}),
    (Mercurial(), [], ['123'], {}),
    (Subversion(), [], ['-r', '123'], {}),
    # Test extra_args.  For this, test using a single VersionControl class.
    (Git(), ['HEAD', 'opt1', 'opt2'], ['123', 'opt1', 'opt2'],
        dict(extra_args=['opt1', 'opt2'])),
])
def test_rev_options_to_args(vcs, expected1, expected2, kwargs):
    """
    Test RevOptions.to_args().
    """
    assert RevOptions(vcs, **kwargs).to_args() == expected1
    assert RevOptions(vcs, '123', **kwargs).to_args() == expected2


def test_rev_options_to_display():
    """
    Test RevOptions.to_display().
    """
    # The choice of VersionControl class doesn't matter here since
    # the implementation is the same for all of them.
    vcs = Git()

    rev_options = RevOptions(vcs)
    assert rev_options.to_display() == ''

    rev_options = RevOptions(vcs, 'master')
    assert rev_options.to_display() == ' (to revision master)'


def test_rev_options_make_new():
    """
    Test RevOptions.make_new().
    """
    # The choice of VersionControl class doesn't matter here since
    # the implementation is the same for all of them.
    vcs = Git()

    rev_options = RevOptions(vcs, 'master', extra_args=['foo', 'bar'])
    new_options = rev_options.make_new('develop')

    assert new_options is not rev_options
    assert new_options.extra_args == ['foo', 'bar']
    assert new_options.rev == 'develop'
    assert new_options.vcs is vcs


@pytest.fixture
def git():
    git_url = 'https://github.com/pypa/pip-test-package'
    sha = '5547fa909e83df8bd743d3978d6667497983a4b7'
    git = Git()
    git.get_url = Mock(return_value=git_url)
    git.get_revision = Mock(return_value=sha)
    return git


@pytest.fixture
def dist():
    dist = Mock()
    dist.egg_name = Mock(return_value='pip_test_package')
    return dist


def test_looks_like_hash():
    assert looks_like_hash(40 * 'a')
    assert looks_like_hash(40 * 'A')
    # Test a string containing all valid characters.
    assert looks_like_hash(18 * 'a' + '0123456789abcdefABCDEF')
    assert not looks_like_hash(40 * 'g')
    assert not looks_like_hash(39 * 'a')


@pytest.mark.network
def test_git_get_src_requirements(git, dist):
    ret = git.get_src_requirement(dist, location='.')

    assert ret == ''.join([
        'git+https://github.com/pypa/pip-test-package',
        '@5547fa909e83df8bd743d3978d6667497983a4b7',
        '#egg=pip_test_package'
    ])


@pytest.mark.parametrize('rev_name,result', (
    ('5547fa909e83df8bd743d3978d6667497983a4b7', True),
    ('5547fa909', False),
    ('5678', False),
    ('abc123', False),
    ('foo', False),
    (None, False),
))
def test_git_is_commit_id_equal(git, rev_name, result):
    """
    Test Git.is_commit_id_equal().
    """
    assert git.is_commit_id_equal('/path', rev_name) is result


def test_translate_egg_surname():
    vc = VersionControl()
    assert vc.translate_egg_surname("foo") == "foo"
    assert vc.translate_egg_surname("foo/bar") == "foo_bar"
    assert vc.translate_egg_surname("foo/1.2.3") == "foo_1.2.3"


# The non-SVN backends all use the same get_netloc_and_auth(), so only test
# Git as a representative.
@pytest.mark.parametrize('netloc, expected', [
    # Test a basic case.
    ('example.com', ('example.com', (None, None))),
    # Test with username and password.
    ('user:pass@example.com', ('user:pass@example.com', (None, None))),
])
def test_git__get_netloc_and_auth(netloc, expected):
    """
    Test VersionControl.get_netloc_and_auth().
    """
    actual = Git().get_netloc_and_auth(netloc)
    assert actual == expected


@pytest.mark.parametrize('netloc, expected', [
    # Test a basic case.
    ('example.com', ('example.com', (None, None))),
    # Test with username and no password.
    ('user@example.com', ('example.com', ('user', None))),
    # Test with username and password.
    ('user:pass@example.com', ('example.com', ('user', 'pass'))),
    # Test the password containing an @ symbol.
    ('user:pass@word@example.com', ('example.com', ('user', 'pass@word'))),
    # Test the password containing a : symbol.
    ('user:pass:word@example.com', ('example.com', ('user', 'pass:word'))),
])
def test_subversion__get_netloc_and_auth(netloc, expected):
    """
    Test Subversion.get_netloc_and_auth().
    """
    actual = Subversion().get_netloc_and_auth(netloc)
    assert actual == expected


def test_git__get_url_rev__idempotent():
    """
    Check that Git.get_url_rev_and_auth() is idempotent for what the code calls
    "stub URLs" (i.e. URLs that don't contain "://").

    Also check that it doesn't change self.url.
    """
    url = 'git+git@git.example.com:MyProject#egg=MyProject'
    vcs = Git(url)
    result1 = vcs.get_url_rev_and_auth(url)
    assert vcs.url == url
    result2 = vcs.get_url_rev_and_auth(url)
    expected = ('git@git.example.com:MyProject', None, (None, None))
    assert result1 == expected
    assert result2 == expected


def test_bazaar__get_url_rev_and_auth():
    """
    Test bzr url support.

    SSH and launchpad have special handling.
    """
    http_bzr_repo = Bazaar(
        url='bzr+http://bzr.myproject.org/MyProject/trunk/#egg=MyProject'
    )
    https_bzr_repo = Bazaar(
        url='bzr+https://bzr.myproject.org/MyProject/trunk/#egg=MyProject'
    )
    ssh_bzr_repo = Bazaar(
        url='bzr+ssh://bzr.myproject.org/MyProject/trunk/#egg=MyProject'
    )
    ftp_bzr_repo = Bazaar(
        url='bzr+ftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject'
    )
    sftp_bzr_repo = Bazaar(
        url='bzr+sftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject'
    )
    launchpad_bzr_repo = Bazaar(
        url='bzr+lp:MyLaunchpadProject#egg=MyLaunchpadProject'
    )

    assert http_bzr_repo.get_url_rev_and_auth(http_bzr_repo.url) == (
        'http://bzr.myproject.org/MyProject/trunk/', None, (None, None),
    )
    assert https_bzr_repo.get_url_rev_and_auth(https_bzr_repo.url) == (
        'https://bzr.myproject.org/MyProject/trunk/', None, (None, None),
    )
    assert ssh_bzr_repo.get_url_rev_and_auth(ssh_bzr_repo.url) == (
        'bzr+ssh://bzr.myproject.org/MyProject/trunk/', None, (None, None),
    )
    assert ftp_bzr_repo.get_url_rev_and_auth(ftp_bzr_repo.url) == (
        'ftp://bzr.myproject.org/MyProject/trunk/', None, (None, None),
    )
    assert sftp_bzr_repo.get_url_rev_and_auth(sftp_bzr_repo.url) == (
        'sftp://bzr.myproject.org/MyProject/trunk/', None, (None, None),
    )
    assert launchpad_bzr_repo.get_url_rev_and_auth(launchpad_bzr_repo.url) == (
        'lp:MyLaunchpadProject', None, (None, None),
    )


# The non-SVN backends all use the same make_rev_args(), so only test
# Git as a representative.
@pytest.mark.parametrize('username, password, expected', [
    (None, None, []),
    ('user', None, []),
    ('user', 'pass', []),
])
def test_git__make_rev_args(username, password, expected):
    """
    Test VersionControl.make_rev_args().
    """
    actual = Git().make_rev_args(username, password)
    assert actual == expected


@pytest.mark.parametrize('username, password, expected', [
    (None, None, []),
    ('user', None, ['--username', 'user']),
    ('user', 'pass', ['--username', 'user', '--password', 'pass']),
])
def test_subversion__make_rev_args(username, password, expected):
    """
    Test Subversion.make_rev_args().
    """
    actual = Subversion().make_rev_args(username, password)
    assert actual == expected


def test_subversion__get_url_rev_options():
    """
    Test Subversion.get_url_rev_options().
    """
    url = 'svn+https://user:pass@svn.example.com/MyProject@v1.0#egg=MyProject'
    url, rev_options = Subversion().get_url_rev_options(url)
    assert url == 'https://svn.example.com/MyProject'
    assert rev_options.rev == 'v1.0'
    assert rev_options.extra_args == (
        ['--username', 'user', '--password', 'pass']
    )


def test_get_git_version():
    git_version = Git().get_git_version()
    assert git_version >= parse_version('1.0.0')
