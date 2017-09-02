import pytest
from mock import Mock
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.vcs import RevOptions, VersionControl
from pip._internal.vcs.bazaar import Bazaar
from pip._internal.vcs.git import Git
from pip._internal.vcs.mercurial import Mercurial
from pip._internal.vcs.subversion import Subversion
from tests.lib import pyversion

if pyversion >= '3':
    VERBOSE_FALSE = False
else:
    VERBOSE_FALSE = 0


def check_to_args(vcs, expected1, expected2):
    """
    Check RevOptions.to_args(), with and without passing a rev to RevOptions.
    """
    assert RevOptions(vcs).to_args(['cmd']) == expected1
    assert RevOptions(vcs, '123').to_args(['cmd']) == expected2


def test_rev_options_to_args():
    """
    Test RevOptions.to_args().
    """
    # Check VCS-specific RevOptions behavior.
    check_to_args(Bazaar(), ['cmd'], ['cmd', '-r', '123'])
    check_to_args(Git(), ['cmd', 'origin/master'], ['cmd', '123'])
    check_to_args(Mercurial(), ['cmd'], ['cmd', '123'])
    check_to_args(Subversion(), ['cmd'], ['cmd', '-r', '123'])

    # Check RevOptions behavior that is the same across all VersionControl
    # classes.  For these, use a single VersionControl class to test.
    vcs = Git()

    # Test start_args.
    rev_options = RevOptions(vcs, 'master')
    assert (
        rev_options.to_args(['cmd', 'option1']) ==
        ['cmd', 'option1', 'master']
    )
    # Test end_args.
    rev_options = RevOptions(vcs, 'master')
    assert (
        rev_options.to_args(['cmd', 'option1'], ['option2']) ==
        ['cmd', 'option1', 'master', 'option2']
    )
    # Test extra_args.
    rev_options = RevOptions(vcs, 'master', extra_args=['option1', 'option2'])
    assert (
        rev_options.to_args(['cmd']) ==
        ['cmd', 'master', 'option1', 'option2']
    )
    # Test extra_args with end_args.
    assert (
        rev_options.to_args(['cmd'], ['option3']) ==
        ['cmd', 'master', 'option1', 'option2', 'option3']
    )


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
    git_url = 'http://github.com/pypa/pip-test-package'
    refs = {
        '0.1': 'a8992fc7ee17e5b9ece022417b64594423caca7c',
        '0.1.1': '7d654e66c8fa7149c165ddeffa5b56bc06619458',
        '0.1.2': 'f1c1020ebac81f9aeb5c766ff7a772f709e696ee',
        'foo': '5547fa909e83df8bd743d3978d6667497983a4b7',
        'bar': '5547fa909e83df8bd743d3978d6667497983a4b7',
        'master': '5547fa909e83df8bd743d3978d6667497983a4b7',
        'origin/master': '5547fa909e83df8bd743d3978d6667497983a4b7',
        'origin/HEAD': '5547fa909e83df8bd743d3978d6667497983a4b7',
    }
    sha = refs['foo']

    git = Git()
    git.get_url = Mock(return_value=git_url)
    git.get_revision = Mock(return_value=sha)
    git.get_short_refs = Mock(return_value=refs)
    return git


@pytest.fixture
def dist():
    dist = Mock()
    dist.egg_name = Mock(return_value='pip_test_package')
    return dist


def test_git_get_src_requirements(git, dist):
    ret = git.get_src_requirement(dist, location='.')

    assert ret == ''.join([
        'git+http://github.com/pypa/pip-test-package',
        '@5547fa909e83df8bd743d3978d6667497983a4b7',
        '#egg=pip_test_package'
    ])


@pytest.mark.parametrize('ref,result', (
    ('5547fa909e83df8bd743d3978d6667497983a4b7', True),
    ('5547fa909', True),
    ('abc123', False),
    ('foo', False),
))
def test_git_check_version(git, ref, result):
    assert git.check_version('foo', ref) is result


def test_translate_egg_surname():
    vc = VersionControl()
    assert vc.translate_egg_surname("foo") == "foo"
    assert vc.translate_egg_surname("foo/bar") == "foo_bar"
    assert vc.translate_egg_surname("foo/1.2.3") == "foo_1.2.3"


def test_bazaar_simple_urls():
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

    assert http_bzr_repo.get_url_rev() == (
        'http://bzr.myproject.org/MyProject/trunk/', None,
    )
    assert https_bzr_repo.get_url_rev() == (
        'https://bzr.myproject.org/MyProject/trunk/', None,
    )
    assert ssh_bzr_repo.get_url_rev() == (
        'bzr+ssh://bzr.myproject.org/MyProject/trunk/', None,
    )
    assert ftp_bzr_repo.get_url_rev() == (
        'ftp://bzr.myproject.org/MyProject/trunk/', None,
    )
    assert sftp_bzr_repo.get_url_rev() == (
        'sftp://bzr.myproject.org/MyProject/trunk/', None,
    )
    assert launchpad_bzr_repo.get_url_rev() == (
        'lp:MyLaunchpadProject', None,
    )


def test_subversion_remove_auth_from_url():
    # Check that the url is doctored appropriately to remove auth elements
    #    from the url
    svn_auth_url = 'https://user:pass@svnrepo.org/svn/project/tags/v0.2'
    expected_url = 'https://svnrepo.org/svn/project/tags/v0.2'
    url = Subversion.remove_auth_from_url(svn_auth_url)
    assert url == expected_url

    # Check that this doesn't impact urls without authentication'
    svn_noauth_url = 'https://svnrepo.org/svn/project/tags/v0.2'
    expected_url = svn_noauth_url
    url = Subversion.remove_auth_from_url(svn_noauth_url)
    assert url == expected_url

    # Check that links to specific revisions are handled properly
    svn_rev_url = 'https://user:pass@svnrepo.org/svn/project/trunk@8181'
    expected_url = 'https://svnrepo.org/svn/project/trunk@8181'
    url = Subversion.remove_auth_from_url(svn_rev_url)
    assert url == expected_url

    svn_rev_url = 'https://svnrepo.org/svn/project/trunk@8181'
    expected_url = 'https://svnrepo.org/svn/project/trunk@8181'
    url = Subversion.remove_auth_from_url(svn_rev_url)
    assert url == expected_url


def test_get_git_version():
    git_version = Git().get_git_version()
    assert git_version >= parse_version('1.0.0')
