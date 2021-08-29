import os
import pathlib
from unittest import TestCase
from unittest.mock import patch

import pytest

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import hide_url, hide_value
from pip._internal.vcs import make_vcs_requirement_url
from pip._internal.vcs.bazaar import Bazaar
from pip._internal.vcs.git import Git, RemoteNotValidError, looks_like_hash
from pip._internal.vcs.mercurial import Mercurial
from pip._internal.vcs.subversion import Subversion
from pip._internal.vcs.versioncontrol import RevOptions, VersionControl
from tests.lib import is_svn_installed, need_svn


@pytest.mark.skipif(
    "CI" not in os.environ, reason="Subversion is only required under CI"
)
def test_ensure_svn_available():
    """Make sure that svn is available when running in CI."""
    assert is_svn_installed()


@pytest.mark.parametrize(
    "args, expected",
    [
        # Test without subdir.
        (
            ("git+https://example.com/pkg", "dev", "myproj"),
            "git+https://example.com/pkg@dev#egg=myproj",
        ),
        # Test with subdir.
        (
            ("git+https://example.com/pkg", "dev", "myproj", "sub/dir"),
            "git+https://example.com/pkg@dev#egg=myproj&subdirectory=sub/dir",
        ),
        # Test with None subdir.
        (
            ("git+https://example.com/pkg", "dev", "myproj", None),
            "git+https://example.com/pkg@dev#egg=myproj",
        ),
        # Test an unescaped project name.
        (
            ("git+https://example.com/pkg", "dev", "zope-interface"),
            "git+https://example.com/pkg@dev#egg=zope_interface",
        ),
    ],
)
def test_make_vcs_requirement_url(args, expected):
    actual = make_vcs_requirement_url(*args)
    assert actual == expected


def test_rev_options_repr():
    rev_options = RevOptions(Git, "develop")
    assert repr(rev_options) == "<RevOptions git: rev='develop'>"


@pytest.mark.parametrize(
    ("vc_class", "expected1", "expected2", "kwargs"),
    [
        # First check VCS-specific RevOptions behavior.
        (Bazaar, [], ["-r", "123"], {}),
        (Git, ["HEAD"], ["123"], {}),
        (Mercurial, [], ["123"], {}),
        (Subversion, [], ["-r", "123"], {}),
        # Test extra_args.  For this, test using a single VersionControl class.
        (
            Git,
            ["HEAD", "opt1", "opt2"],
            ["123", "opt1", "opt2"],
            dict(extra_args=["opt1", "opt2"]),
        ),
    ],
)
def test_rev_options_to_args(vc_class, expected1, expected2, kwargs):
    """
    Test RevOptions.to_args().
    """
    assert RevOptions(vc_class, **kwargs).to_args() == expected1
    assert RevOptions(vc_class, "123", **kwargs).to_args() == expected2


def test_rev_options_to_display():
    """
    Test RevOptions.to_display().
    """
    # The choice of VersionControl class doesn't matter here since
    # the implementation is the same for all of them.
    rev_options = RevOptions(Git)
    assert rev_options.to_display() == ""

    rev_options = RevOptions(Git, "master")
    assert rev_options.to_display() == " (to revision master)"


def test_rev_options_make_new():
    """
    Test RevOptions.make_new().
    """
    # The choice of VersionControl class doesn't matter here since
    # the implementation is the same for all of them.
    rev_options = RevOptions(Git, "master", extra_args=["foo", "bar"])
    new_options = rev_options.make_new("develop")

    assert new_options is not rev_options
    assert new_options.extra_args == ["foo", "bar"]
    assert new_options.rev == "develop"
    assert new_options.vc_class is Git


@pytest.mark.parametrize(
    "sha, expected",
    [
        ((40 * "a"), True),
        ((40 * "A"), True),
        # Test a string containing all valid characters.
        ((18 * "a" + "0123456789abcdefABCDEF"), True),
        ((40 * "g"), False),
        ((39 * "a"), False),
        ((41 * "a"), False),
    ],
)
def test_looks_like_hash(sha, expected):
    assert looks_like_hash(sha) == expected


@pytest.mark.parametrize(
    "vcs_cls, remote_url, expected",
    [
        # Mercurial is one of the subclasses using the base class implementation.
        # `hg://` isn't a real prefix but it tests the default behaviour.
        (Mercurial, "hg://user@example.com/MyProject", False),
        (Mercurial, "http://example.com/MyProject", True),
        # The Git subclasses should return true in all cases.
        (Git, "git://example.com/MyProject", True),
        (Git, "http://example.com/MyProject", True),
        # Subversion also overrides the base class implementation.
        (Subversion, "svn://example.com/MyProject", True),
    ],
)
def test_should_add_vcs_url_prefix(vcs_cls, remote_url, expected):
    actual = vcs_cls.should_add_vcs_url_prefix(remote_url)
    assert actual == expected


@pytest.mark.parametrize(
    "url, target",
    [
        # A fully qualified remote url. No changes needed.
        ("ssh://bob@server/foo/bar.git", "ssh://bob@server/foo/bar.git"),
        ("git://bob@server/foo/bar.git", "git://bob@server/foo/bar.git"),
        # User is optional and does not need a default.
        ("ssh://server/foo/bar.git", "ssh://server/foo/bar.git"),
        # The common scp shorthand for ssh remotes. Pip won't recognise these as
        # git remotes until they have a 'ssh://' prefix and the ':' in the middle
        # is gone.
        ("git@example.com:foo/bar.git", "ssh://git@example.com/foo/bar.git"),
        ("example.com:foo.git", "ssh://example.com/foo.git"),
        # Http(s) remote names are already complete and should remain unchanged.
        ("https://example.com/foo", "https://example.com/foo"),
        ("http://example.com/foo/bar.git", "http://example.com/foo/bar.git"),
        ("https://bob@example.com/foo", "https://bob@example.com/foo"),
    ],
)
def test_git_remote_url_to_pip(url, target):
    assert Git._git_remote_to_pip_url(url) == target


@pytest.mark.parametrize(
    "url, platform",
    [
        # Windows paths with the ':' drive prefix look dangerously close to SCP.
        ("c:/piffle/wiffle/waffle/poffle.git", "nt"),
        (r"c:\faffle\waffle\woffle\piffle.git", "nt"),
        # Unix paths less so but test them anyway.
        ("/muffle/fuffle/pufffle/fluffle.git", "posix"),
    ],
)
def test_paths_are_not_mistaken_for_scp_shorthand(url, platform):
    # File paths should not be mistaken for SCP shorthand. If they do then
    # 'c:/piffle/wiffle' would end up as 'ssh://c/piffle/wiffle'.
    from pip._internal.vcs.git import SCP_REGEX

    assert not SCP_REGEX.match(url)

    if platform == os.name:
        with pytest.raises(RemoteNotValidError):
            Git._git_remote_to_pip_url(url)


def test_git_remote_local_path(tmpdir):
    path = pathlib.Path(tmpdir, "project.git")
    path.mkdir()
    # Path must exist to be recognised as a local git remote.
    assert Git._git_remote_to_pip_url(str(path)) == path.as_uri()


@patch("pip._internal.vcs.git.Git.get_remote_url")
@patch("pip._internal.vcs.git.Git.get_revision")
@patch("pip._internal.vcs.git.Git.get_subdirectory")
@pytest.mark.parametrize(
    "git_url, target_url_prefix",
    [
        (
            "https://github.com/pypa/pip-test-package",
            "git+https://github.com/pypa/pip-test-package",
        ),
        (
            "git@github.com:pypa/pip-test-package",
            "git+ssh://git@github.com/pypa/pip-test-package",
        ),
    ],
    ids=["https", "ssh"],
)
@pytest.mark.network
def test_git_get_src_requirements(
    mock_get_subdirectory,
    mock_get_revision,
    mock_get_remote_url,
    git_url,
    target_url_prefix,
):
    sha = "5547fa909e83df8bd743d3978d6667497983a4b7"

    mock_get_remote_url.return_value = Git._git_remote_to_pip_url(git_url)
    mock_get_revision.return_value = sha
    mock_get_subdirectory.return_value = None

    ret = Git.get_src_requirement(".", "pip-test-package")

    target = f"{target_url_prefix}@{sha}#egg=pip_test_package"
    assert ret == target


@patch("pip._internal.vcs.git.Git.get_revision_sha")
def test_git_resolve_revision_rev_exists(get_sha_mock):
    get_sha_mock.return_value = ("123456", False)
    url = "git+https://git.example.com"
    rev_options = Git.make_rev_options("develop")

    new_options = Git.resolve_revision(".", url, rev_options)
    assert new_options.rev == "123456"


@patch("pip._internal.vcs.git.Git.get_revision_sha")
def test_git_resolve_revision_rev_not_found(get_sha_mock):
    get_sha_mock.return_value = (None, False)
    url = "git+https://git.example.com"
    rev_options = Git.make_rev_options("develop")

    new_options = Git.resolve_revision(".", url, rev_options)
    assert new_options.rev == "develop"


@patch("pip._internal.vcs.git.Git.get_revision_sha")
def test_git_resolve_revision_not_found_warning(get_sha_mock, caplog):
    get_sha_mock.return_value = (None, False)
    url = "git+https://git.example.com"
    sha = 40 * "a"
    rev_options = Git.make_rev_options(sha)

    # resolve_revision with a full sha would fail here because
    # it attempts a git fetch. This case is now covered by
    # test_resolve_commit_not_on_branch.

    rev_options = Git.make_rev_options(sha[:6])
    new_options = Git.resolve_revision(".", url, rev_options)
    assert new_options.rev == "aaaaaa"

    # Check that a warning got logged only for the abbreviated hash.
    messages = [r.getMessage() for r in caplog.records]
    messages = [msg for msg in messages if msg.startswith("Did not find ")]
    assert messages == [
        "Did not find branch or tag 'aaaaaa', assuming revision or ref."
    ]


@pytest.mark.parametrize(
    "rev_name,result",
    (
        ("5547fa909e83df8bd743d3978d6667497983a4b7", True),
        ("5547fa909", False),
        ("5678", False),
        ("abc123", False),
        ("foo", False),
        (None, False),
    ),
)
@patch("pip._internal.vcs.git.Git.get_revision")
def test_git_is_commit_id_equal(mock_get_revision, rev_name, result):
    """
    Test Git.is_commit_id_equal().
    """
    mock_get_revision.return_value = "5547fa909e83df8bd743d3978d6667497983a4b7"
    assert Git.is_commit_id_equal("/path", rev_name) is result


# The non-SVN backends all use the same get_netloc_and_auth(), so only test
# Git as a representative.
@pytest.mark.parametrize(
    "args, expected",
    [
        # Test a basic case.
        (("example.com", "https"), ("example.com", (None, None))),
        # Test with username and password.
        (("user:pass@example.com", "https"), ("user:pass@example.com", (None, None))),
    ],
)
def test_git__get_netloc_and_auth(args, expected):
    """
    Test VersionControl.get_netloc_and_auth().
    """
    netloc, scheme = args
    actual = Git.get_netloc_and_auth(netloc, scheme)
    assert actual == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        # Test https.
        (("example.com", "https"), ("example.com", (None, None))),
        # Test https with username and no password.
        (("user@example.com", "https"), ("example.com", ("user", None))),
        # Test https with username and password.
        (("user:pass@example.com", "https"), ("example.com", ("user", "pass"))),
        # Test https with URL-encoded reserved characters.
        (
            ("user%3Aname:%23%40%5E@example.com", "https"),
            ("example.com", ("user:name", "#@^")),
        ),
        # Test ssh with username and password.
        (("user:pass@example.com", "ssh"), ("user:pass@example.com", (None, None))),
    ],
)
def test_subversion__get_netloc_and_auth(args, expected):
    """
    Test Subversion.get_netloc_and_auth().
    """
    netloc, scheme = args
    actual = Subversion.get_netloc_and_auth(netloc, scheme)
    assert actual == expected


def test_git__get_url_rev__idempotent():
    """
    Check that Git.get_url_rev_and_auth() is idempotent for what the code calls
    "stub URLs" (i.e. URLs that don't contain "://").

    Also check that it doesn't change self.url.
    """
    url = "git+git@git.example.com:MyProject#egg=MyProject"
    result1 = Git.get_url_rev_and_auth(url)
    result2 = Git.get_url_rev_and_auth(url)
    expected = ("git@git.example.com:MyProject", None, (None, None))
    assert result1 == expected
    assert result2 == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "svn+https://svn.example.com/MyProject",
            ("https://svn.example.com/MyProject", None, (None, None)),
        ),
        # Test a "+" in the path portion.
        (
            "svn+https://svn.example.com/My+Project",
            ("https://svn.example.com/My+Project", None, (None, None)),
        ),
    ],
)
def test_version_control__get_url_rev_and_auth(url, expected):
    """
    Test the basic case of VersionControl.get_url_rev_and_auth().
    """
    actual = VersionControl.get_url_rev_and_auth(url)
    assert actual == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://svn.example.com/MyProject",
        # Test a URL containing a "+" (but not in the scheme).
        "https://svn.example.com/My+Project",
    ],
)
def test_version_control__get_url_rev_and_auth__missing_plus(url):
    """
    Test passing a URL to VersionControl.get_url_rev_and_auth() with a "+"
    missing from the scheme.
    """
    with pytest.raises(ValueError) as excinfo:
        VersionControl.get_url_rev_and_auth(url)

    assert "malformed VCS url" in str(excinfo.value)


@pytest.mark.parametrize(
    "url",
    [
        # Test a URL with revision part as empty.
        "git+https://github.com/MyUser/myProject.git@#egg=py_pkg",
    ],
)
def test_version_control__get_url_rev_and_auth__no_revision(url):
    """
    Test passing a URL to VersionControl.get_url_rev_and_auth() with
    empty revision
    """
    with pytest.raises(InstallationError) as excinfo:
        VersionControl.get_url_rev_and_auth(url)

    assert "an empty revision (after @)" in str(excinfo.value)


@pytest.mark.parametrize("vcs_cls", [Bazaar, Git, Mercurial, Subversion])
@pytest.mark.parametrize(
    "exc_cls, msg_re",
    [
        (FileNotFoundError, r"Cannot find command '{name}'"),
        (PermissionError, r"No permission to execute '{name}'"),
    ],
    ids=["FileNotFoundError", "PermissionError"],
)
def test_version_control__run_command__fails(vcs_cls, exc_cls, msg_re):
    """
    Test that ``VersionControl.run_command()`` raises ``BadCommand``
    when the command is not found or when the user have no permission
    to execute it. The error message must contains the command name.
    """
    with patch("pip._internal.vcs.versioncontrol.call_subprocess") as call:
        call.side_effect = exc_cls
        with pytest.raises(BadCommand, match=msg_re.format(name=vcs_cls.name)):
            vcs_cls.run_command([])


@pytest.mark.parametrize(
    "url, expected",
    [
        # Test http.
        (
            "bzr+http://bzr.myproject.org/MyProject/trunk/#egg=MyProject",
            "http://bzr.myproject.org/MyProject/trunk/",
        ),
        # Test https.
        (
            "bzr+https://bzr.myproject.org/MyProject/trunk/#egg=MyProject",
            "https://bzr.myproject.org/MyProject/trunk/",
        ),
        # Test ftp.
        (
            "bzr+ftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject",
            "ftp://bzr.myproject.org/MyProject/trunk/",
        ),
        # Test sftp.
        (
            "bzr+sftp://bzr.myproject.org/MyProject/trunk/#egg=MyProject",
            "sftp://bzr.myproject.org/MyProject/trunk/",
        ),
        # Test launchpad.
        ("bzr+lp:MyLaunchpadProject#egg=MyLaunchpadProject", "lp:MyLaunchpadProject"),
        # Test ssh (special handling).
        (
            "bzr+ssh://bzr.myproject.org/MyProject/trunk/#egg=MyProject",
            "bzr+ssh://bzr.myproject.org/MyProject/trunk/",
        ),
    ],
)
def test_bazaar__get_url_rev_and_auth(url, expected):
    """
    Test Bazaar.get_url_rev_and_auth().
    """
    actual = Bazaar.get_url_rev_and_auth(url)
    assert actual == (expected, None, (None, None))


@pytest.mark.parametrize(
    "url, expected",
    [
        # Test an https URL.
        (
            "svn+https://svn.example.com/MyProject#egg=MyProject",
            ("https://svn.example.com/MyProject", None, (None, None)),
        ),
        # Test an https URL with a username and password.
        (
            "svn+https://user:pass@svn.example.com/MyProject#egg=MyProject",
            ("https://svn.example.com/MyProject", None, ("user", "pass")),
        ),
        # Test an ssh URL.
        (
            "svn+ssh://svn.example.com/MyProject#egg=MyProject",
            ("svn+ssh://svn.example.com/MyProject", None, (None, None)),
        ),
        # Test an ssh URL with a username.
        (
            "svn+ssh://user@svn.example.com/MyProject#egg=MyProject",
            ("svn+ssh://user@svn.example.com/MyProject", None, (None, None)),
        ),
    ],
)
def test_subversion__get_url_rev_and_auth(url, expected):
    """
    Test Subversion.get_url_rev_and_auth().
    """
    actual = Subversion.get_url_rev_and_auth(url)
    assert actual == expected


# The non-SVN backends all use the same make_rev_args(), so only test
# Git as a representative.
@pytest.mark.parametrize(
    "username, password, expected",
    [
        (None, None, []),
        ("user", None, []),
        ("user", hide_value("pass"), []),
    ],
)
def test_git__make_rev_args(username, password, expected):
    """
    Test VersionControl.make_rev_args().
    """
    actual = Git.make_rev_args(username, password)
    assert actual == expected


@pytest.mark.parametrize(
    "username, password, expected",
    [
        (None, None, []),
        ("user", None, ["--username", "user"]),
        (
            "user",
            hide_value("pass"),
            ["--username", "user", "--password", hide_value("pass")],
        ),
    ],
)
def test_subversion__make_rev_args(username, password, expected):
    """
    Test Subversion.make_rev_args().
    """
    actual = Subversion.make_rev_args(username, password)
    assert actual == expected


def test_subversion__get_url_rev_options():
    """
    Test Subversion.get_url_rev_options().
    """
    secret_url = "svn+https://user:pass@svn.example.com/MyProject@v1.0#egg=MyProject"
    hidden_url = hide_url(secret_url)
    url, rev_options = Subversion().get_url_rev_options(hidden_url)
    assert url == hide_url("https://svn.example.com/MyProject")
    assert rev_options.rev == "v1.0"
    assert rev_options.extra_args == (
        ["--username", "user", "--password", hide_value("pass")]
    )


def test_get_git_version():
    git_version = Git().get_git_version()
    assert git_version >= (1, 0, 0)


@pytest.mark.parametrize(
    "use_interactive,is_atty,expected",
    [
        (None, False, False),
        (None, True, True),
        (False, False, False),
        (False, True, False),
        (True, False, True),
        (True, True, True),
    ],
)
@patch("sys.stdin.isatty")
def test_subversion__init_use_interactive(
    mock_isatty, use_interactive, is_atty, expected
):
    """
    Test Subversion.__init__() with mocked sys.stdin.isatty() output.
    """
    mock_isatty.return_value = is_atty
    svn = Subversion(use_interactive=use_interactive)
    assert svn.use_interactive == expected


@need_svn
def test_subversion__call_vcs_version():
    """
    Test Subversion.call_vcs_version() against local ``svn``.
    """
    version = Subversion().call_vcs_version()
    # All Subversion releases since 1.0.0 have used three parts.
    assert len(version) == 3
    for part in version:
        assert isinstance(part, int)
    assert version[0] >= 1


@pytest.mark.parametrize(
    "svn_output, expected_version",
    [
        (
            "svn, version 1.10.3 (r1842928)\n"
            "   compiled Feb 25 2019, 14:20:39 on x86_64-apple-darwin17.0.0",
            (1, 10, 3),
        ),
        (
            "svn, version 1.12.0-SlikSvn (SlikSvn/1.12.0)\n"
            "   compiled May 28 2019, 13:44:56 on x86_64-microsoft-windows6.2",
            (1, 12, 0),
        ),
        ("svn, version 1.9.7 (r1800392)", (1, 9, 7)),
        ("svn, version 1.9.7a1 (r1800392)", ()),
        ("svn, version 1.9 (r1800392)", (1, 9)),
        ("svn, version .9.7 (r1800392)", ()),
        ("svn version 1.9.7 (r1800392)", ()),
        ("svn 1.9.7", ()),
        ("svn, version . .", ()),
        ("", ()),
    ],
)
@patch("pip._internal.vcs.subversion.Subversion.run_command")
def test_subversion__call_vcs_version_patched(
    mock_run_command, svn_output, expected_version
):
    """
    Test Subversion.call_vcs_version() against patched output.
    """
    mock_run_command.return_value = svn_output
    version = Subversion().call_vcs_version()
    assert version == expected_version


@patch("pip._internal.vcs.subversion.Subversion.run_command")
def test_subversion__call_vcs_version_svn_not_installed(mock_run_command):
    """
    Test Subversion.call_vcs_version() when svn is not installed.
    """
    mock_run_command.side_effect = BadCommand
    with pytest.raises(BadCommand):
        Subversion().call_vcs_version()


@pytest.mark.parametrize(
    "version",
    [
        (),
        (1,),
        (1, 8),
        (1, 8, 0),
    ],
)
def test_subversion__get_vcs_version_cached(version):
    """
    Test Subversion.get_vcs_version() with previously cached result.
    """
    svn = Subversion()
    svn._vcs_version = version
    assert svn.get_vcs_version() == version


@pytest.mark.parametrize(
    "vcs_version",
    [
        (),
        (1, 7),
        (1, 8, 0),
    ],
)
@patch("pip._internal.vcs.subversion.Subversion.call_vcs_version")
def test_subversion__get_vcs_version_call_vcs(mock_call_vcs, vcs_version):
    """
    Test Subversion.get_vcs_version() with mocked output from
    call_vcs_version().
    """
    mock_call_vcs.return_value = vcs_version
    svn = Subversion()
    assert svn.get_vcs_version() == vcs_version

    # Check that the version information is cached.
    assert svn._vcs_version == vcs_version


@pytest.mark.parametrize(
    "use_interactive,vcs_version,expected_options",
    [
        (False, (), ["--non-interactive"]),
        (False, (1, 7, 0), ["--non-interactive"]),
        (False, (1, 8, 0), ["--non-interactive"]),
        (True, (), []),
        (True, (1, 7, 0), []),
        (True, (1, 8, 0), ["--force-interactive"]),
    ],
)
def test_subversion__get_remote_call_options(
    use_interactive, vcs_version, expected_options
):
    """
    Test Subversion.get_remote_call_options().
    """
    svn = Subversion(use_interactive=use_interactive)
    svn._vcs_version = vcs_version
    assert svn.get_remote_call_options() == expected_options


class TestSubversionArgs(TestCase):
    def setUp(self):
        patcher = patch("pip._internal.vcs.versioncontrol.call_subprocess")
        self.addCleanup(patcher.stop)
        self.call_subprocess_mock = patcher.start()

        # Test Data.
        self.url = "svn+http://username:password@svn.example.com/"
        # use_interactive is set to False to test that remote call options are
        # properly added.
        self.svn = Subversion(use_interactive=False)
        self.rev_options = RevOptions(Subversion)
        self.dest = "/tmp/test"

    def assert_call_args(self, args):
        assert self.call_subprocess_mock.call_args[0][0] == args

    def test_obtain(self):
        self.svn.obtain(self.dest, hide_url(self.url))
        self.assert_call_args(
            [
                "svn",
                "checkout",
                "-q",
                "--non-interactive",
                "--username",
                "username",
                "--password",
                hide_value("password"),
                hide_url("http://svn.example.com/"),
                "/tmp/test",
            ]
        )

    def test_fetch_new(self):
        self.svn.fetch_new(self.dest, hide_url(self.url), self.rev_options)
        self.assert_call_args(
            [
                "svn",
                "checkout",
                "-q",
                "--non-interactive",
                hide_url("svn+http://username:password@svn.example.com/"),
                "/tmp/test",
            ]
        )

    def test_fetch_new_revision(self):
        rev_options = RevOptions(Subversion, "123")
        self.svn.fetch_new(self.dest, hide_url(self.url), rev_options)
        self.assert_call_args(
            [
                "svn",
                "checkout",
                "-q",
                "--non-interactive",
                "-r",
                "123",
                hide_url("svn+http://username:password@svn.example.com/"),
                "/tmp/test",
            ]
        )

    def test_switch(self):
        self.svn.switch(self.dest, hide_url(self.url), self.rev_options)
        self.assert_call_args(
            [
                "svn",
                "switch",
                "--non-interactive",
                hide_url("svn+http://username:password@svn.example.com/"),
                "/tmp/test",
            ]
        )

    def test_update(self):
        self.svn.update(self.dest, hide_url(self.url), self.rev_options)
        self.assert_call_args(
            [
                "svn",
                "update",
                "--non-interactive",
                "/tmp/test",
            ]
        )
