from tests.lib import pyversion
from pip.vcs.bazaar import Bazaar
from pip.vcs.subversion import Subversion

if pyversion >= '3':
    VERBOSE_FALSE = False
else:
    VERBOSE_FALSE = 0


def test_bazaar_simple_urls():
    """
    Test bzr url support.

    SSH and launchpad have special handling.
    """
    http_bzr_repo = Bazaar(url='bzr+http://bzr.myproject.org/MyProject/trunk/#egg=MyProject')
    https_bzr_repo = Bazaar(url='bzr+https://bzr.myproject.org/MyProject/trunk/#egg=MyProject')
    ssh_bzr_repo = Bazaar(url='bzr+ssh://bzr.myproject.org/MyProject/trunk/#egg=MyProject')
    ftp_bzr_repo = Bazaar(url='bzr+ftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject')
    sftp_bzr_repo = Bazaar(url='bzr+sftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject')
    launchpad_bzr_repo = Bazaar(url='bzr+lp:MyLaunchpadProject#egg=MyLaunchpadProject')

    assert http_bzr_repo.get_url_rev() == ('http://bzr.myproject.org/MyProject/trunk/', None)
    assert https_bzr_repo.get_url_rev() == ('https://bzr.myproject.org/MyProject/trunk/', None)
    assert ssh_bzr_repo.get_url_rev() == ('bzr+ssh://bzr.myproject.org/MyProject/trunk/', None)
    assert ftp_bzr_repo.get_url_rev() == ('ftp://bzr.myproject.org/MyProject/trunk/', None)
    assert sftp_bzr_repo.get_url_rev() == ('sftp://bzr.myproject.org/MyProject/trunk/', None)
    assert launchpad_bzr_repo.get_url_rev() == ('lp:MyLaunchpadProject', None)

def test_svn_extra_rev_from_url():
    svn_repo_w_rev = Subversion(url="svn+svn://example.com/path/to/project@100")
    assert svn_repo_w_rev.get_url_rev() == ("svn+svn://example.com/path/to/project@100", 100)

    svn_repo_wo_rev = Subversion(url="svn+svn://example.com/path/to/project")
    assert svn_repo_w_rev.get_url_rev() == ("svn+svn://example.com/path/to/project", None)
