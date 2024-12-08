"""
Contains functional tests of the Git class.
"""

import logging
import os
import pathlib
from typing import List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

from pip._internal.utils.misc import HiddenText
from pip._internal.vcs import vcs
from pip._internal.vcs.git import Git, RemoteNotFoundError

from tests.lib import PipTestEnvironment, _create_test_package, _git_commit


def test_get_backend_for_scheme() -> None:
    assert vcs.get_backend_for_scheme("git+https") is vcs.get_backend("Git")


def get_head_sha(script: PipTestEnvironment, dest: str) -> str:
    """Return the HEAD sha."""
    result = script.run("git", "rev-parse", "HEAD", cwd=dest)
    sha = result.stdout.strip()

    return sha


def checkout_ref(script: PipTestEnvironment, repo_dir: str, ref: str) -> None:
    script.run("git", "checkout", ref, cwd=repo_dir)


def checkout_new_branch(script: PipTestEnvironment, repo_dir: str, branch: str) -> None:
    script.run(
        "git",
        "checkout",
        "-b",
        branch,
        cwd=repo_dir,
    )


def do_commit(script: PipTestEnvironment, dest: str) -> str:
    _git_commit(script, dest, message="test commit", allow_empty=True)
    return get_head_sha(script, dest)


def add_commits(script: PipTestEnvironment, dest: str, count: int) -> List[str]:
    """Return a list of the commit hashes from oldest to newest."""
    shas = []
    for _ in range(count):
        sha = do_commit(script, dest)
        shas.append(sha)

    return shas


def check_rev(repo_dir: str, rev: str, expected: Tuple[Optional[str], bool]) -> None:
    assert Git.get_revision_sha(repo_dir, rev) == expected


def test_git_dir_ignored(tmpdir: pathlib.Path) -> None:
    """
    Test that a GIT_DIR environment variable is ignored.
    """
    repo_path = tmpdir / "test-repo"
    repo_path.mkdir()
    repo_dir = str(repo_path)

    env = {"GIT_DIR": "foo"}
    # If GIT_DIR is not ignored, then os.listdir() will return ['foo'].
    Git.run_command(["init", repo_dir], cwd=repo_dir, extra_environ=env)
    assert os.listdir(repo_dir) == [".git"]


def test_git_work_tree_ignored(tmpdir: pathlib.Path) -> None:
    """
    Test that a GIT_WORK_TREE environment variable is ignored.
    """
    repo_path = tmpdir / "test-repo"
    repo_path.mkdir()
    repo_dir = str(repo_path)

    Git.run_command(["init", repo_dir], cwd=repo_dir)
    # Choose a directory relative to the cwd that does not exist.
    # If GIT_WORK_TREE is not ignored, then the command will error out
    # with: "fatal: This operation must be run in a work tree".
    env = {"GIT_WORK_TREE": "foo"}
    Git.run_command(["status", repo_dir], extra_environ=env, cwd=repo_dir)


def test_get_remote_url(script: PipTestEnvironment, tmpdir: pathlib.Path) -> None:
    source_path = tmpdir / "source"
    source_path.mkdir()
    source_url = source_path.as_uri()

    source_dir = str(source_path)
    script.run("git", "init", cwd=source_dir)
    do_commit(script, source_dir)

    repo_dir = str(tmpdir / "repo")
    script.run("git", "clone", source_url, repo_dir)

    remote_url = Git.get_remote_url(repo_dir)
    assert remote_url == source_url


def test_get_remote_url__no_remote(
    script: PipTestEnvironment, tmpdir: pathlib.Path
) -> None:
    """
    Test a repo with no remote.
    """
    repo_path = tmpdir / "temp-repo"
    repo_path.mkdir()
    repo_dir = str(repo_path)

    script.run("git", "init", cwd=repo_dir)

    with pytest.raises(RemoteNotFoundError):
        Git.get_remote_url(repo_dir)


def test_get_current_branch(script: PipTestEnvironment) -> None:
    repo_dir = str(script.scratch_path)

    script.run("git", "init", cwd=repo_dir)
    sha = do_commit(script, repo_dir)

    assert Git.get_current_branch(repo_dir) == "master"

    # Switch to a branch with the same SHA as "master" but whose name
    # is alphabetically after.
    checkout_new_branch(script, repo_dir, "release")
    assert Git.get_current_branch(repo_dir) == "release"

    # Also test the detached HEAD case.
    checkout_ref(script, repo_dir, sha)
    assert Git.get_current_branch(repo_dir) is None


def test_get_current_branch__branch_and_tag_same_name(
    script: PipTestEnvironment, tmpdir: pathlib.Path
) -> None:
    """
    Check calling get_current_branch() from a branch or tag when the branch
    and tag have the same name.
    """
    repo_dir = str(tmpdir)
    script.run("git", "init", cwd=repo_dir)
    do_commit(script, repo_dir)
    checkout_new_branch(script, repo_dir, "dev")
    # Create a tag with the same name as the branch.
    script.run("git", "tag", "dev", cwd=repo_dir)

    assert Git.get_current_branch(repo_dir) == "dev"

    # Now try with the tag checked out.
    checkout_ref(script, repo_dir, "refs/tags/dev")
    assert Git.get_current_branch(repo_dir) is None


def test_get_revision_sha(script: PipTestEnvironment) -> None:
    repo_dir = str(script.scratch_path)

    script.run("git", "init", cwd=repo_dir)
    shas = add_commits(script, repo_dir, count=3)

    tag_sha = shas[0]
    origin_sha = shas[1]
    head_sha = shas[2]
    assert head_sha == shas[-1]

    origin_ref = "refs/remotes/origin/origin-branch"
    generic_ref = "refs/generic-ref"

    script.run("git", "branch", "local-branch", head_sha, cwd=repo_dir)
    script.run("git", "tag", "v1.0", tag_sha, cwd=repo_dir)
    script.run("git", "update-ref", origin_ref, origin_sha, cwd=repo_dir)
    script.run(
        "git",
        "update-ref",
        "refs/remotes/upstream/upstream-branch",
        head_sha,
        cwd=repo_dir,
    )
    script.run("git", "update-ref", generic_ref, head_sha, cwd=repo_dir)

    # Test two tags pointing to the same sha.
    script.run("git", "tag", "v2.0", tag_sha, cwd=repo_dir)
    # Test tags sharing the same suffix as another tag, both before and
    # after the suffix alphabetically.
    script.run("git", "tag", "aaa/v1.0", head_sha, cwd=repo_dir)
    script.run("git", "tag", "zzz/v1.0", head_sha, cwd=repo_dir)

    check_rev(repo_dir, "v1.0", (tag_sha, False))
    check_rev(repo_dir, "v2.0", (tag_sha, False))
    check_rev(repo_dir, "origin-branch", (origin_sha, True))

    ignored_names = [
        # Local branches should be ignored.
        "local-branch",
        # Non-origin remote branches should be ignored.
        "upstream-branch",
        # Generic refs should be ignored.
        "generic-ref",
        # Fully spelled-out refs should be ignored.
        origin_ref,
        generic_ref,
        # Test passing a valid commit hash.
        tag_sha,
        # Test passing a non-existent name.
        "does-not-exist",
    ]
    for name in ignored_names:
        check_rev(repo_dir, name, (None, False))


def test_is_commit_id_equal(script: PipTestEnvironment) -> None:
    """
    Test Git.is_commit_id_equal().
    """
    version_pkg_path = os.fspath(_create_test_package(script.scratch_path))
    script.run("git", "branch", "branch0.1", cwd=version_pkg_path)
    commit = script.run("git", "rev-parse", "HEAD", cwd=version_pkg_path).stdout.strip()

    assert Git.is_commit_id_equal(version_pkg_path, commit)
    assert not Git.is_commit_id_equal(version_pkg_path, commit[:7])
    assert not Git.is_commit_id_equal(version_pkg_path, "branch0.1")
    assert not Git.is_commit_id_equal(version_pkg_path, "abc123")
    # Also check passing a None value.
    assert not Git.is_commit_id_equal(version_pkg_path, None)


def test_is_immutable_rev_checkout(script: PipTestEnvironment) -> None:
    version_pkg_path = os.fspath(_create_test_package(script.scratch_path))
    commit = script.run("git", "rev-parse", "HEAD", cwd=version_pkg_path).stdout.strip()
    assert Git().is_immutable_rev_checkout(
        "git+https://g.c/o/r@" + commit, version_pkg_path
    )
    assert not Git().is_immutable_rev_checkout("git+https://g.c/o/r", version_pkg_path)
    assert not Git().is_immutable_rev_checkout(
        "git+https://g.c/o/r@master", version_pkg_path
    )


def test_get_repository_root(script: PipTestEnvironment) -> None:
    version_pkg_path = _create_test_package(script.scratch_path)
    tests_path = version_pkg_path.joinpath("tests")
    tests_path.mkdir()

    root1 = Git.get_repository_root(os.fspath(version_pkg_path))
    assert root1 is not None
    assert os.path.normcase(root1) == os.path.normcase(version_pkg_path)

    root2 = Git.get_repository_root(os.fspath(tests_path))
    assert root2 is not None
    assert os.path.normcase(root2) == os.path.normcase(version_pkg_path)


def test_resolve_commit_not_on_branch(
    script: PipTestEnvironment, tmp_path: pathlib.Path
) -> None:
    repo_path = tmp_path / "repo"
    repo_file = repo_path / "file.txt"
    clone_path = repo_path / "clone"
    repo_path.mkdir()
    script.run("git", "init", cwd=str(repo_path))

    repo_file.write_text(".")
    script.run("git", "add", "file.txt", cwd=str(repo_path))
    script.run("git", "commit", "-m", "initial commit", cwd=str(repo_path))
    script.run("git", "checkout", "-b", "abranch", cwd=str(repo_path))

    # create a commit
    repo_file.write_text("..")
    script.run("git", "commit", "-a", "-m", "commit 1", cwd=str(repo_path))
    commit = script.run("git", "rev-parse", "HEAD", cwd=str(repo_path)).stdout.strip()

    # make sure our commit is not on a branch
    script.run("git", "checkout", "master", cwd=str(repo_path))
    script.run("git", "branch", "-D", "abranch", cwd=str(repo_path))

    # create a ref that points to our commit
    (repo_path / ".git" / "refs" / "myrefs").mkdir(parents=True)
    (repo_path / ".git" / "refs" / "myrefs" / "myref").write_text(commit)

    # check we can fetch our commit
    rev_options = Git.make_rev_options(commit)
    Git().fetch_new(
        str(clone_path),
        HiddenText(repo_path.as_uri(), redacted="*"),
        rev_options,
        verbosity=0,
    )


def _initialize_clonetest_server(
    repo_path: pathlib.Path, script: PipTestEnvironment, enable_partial_clone: bool
) -> pathlib.Path:
    repo_path.mkdir()
    script.run("git", "init", cwd=str(repo_path))
    repo_file = repo_path / "file.txt"
    repo_file.write_text(".")
    script.run("git", "add", "file.txt", cwd=str(repo_path))
    script.run("git", "commit", "-m", "initial commit", cwd=str(repo_path))

    # Enable filtering support on server
    if enable_partial_clone:
        script.run("git", "config", "uploadpack.allowFilter", "true", cwd=repo_path)
        script.run(
            "git", "config", "uploadpack.allowanysha1inwant", "true", cwd=repo_path
        )

    return repo_file


@pytest.mark.parametrize(
    "version_out, expected_message",
    [
        ("git version -2.25.1", "Can't parse git version: git version -2.25.1"),
        ("git version 2.a.1", "Can't parse git version: git version 2.a.1"),
        ("git ver. 2.25.1", "Can't parse git version: git ver. 2.25.1"),
    ],
)
@patch("pip._internal.vcs.versioncontrol.VersionControl.run_command")
def test_git_parse_fail_warning(
    mock_run_command: Mock,
    caplog: pytest.LogCaptureFixture,
    version_out: str,
    expected_message: str,
) -> None:
    """Test invalid git version logs adds an explicit warning log."""
    mock_run_command.return_value = version_out

    caplog.set_level(logging.WARNING)

    git_tuple = Git().get_git_version()
    # Returns an empty tuple if it is an invalid git version
    assert git_tuple == ()

    # Check for warning log
    assert expected_message in caplog.text.strip()


@pytest.mark.skipif(Git().get_git_version() < (2, 17), reason="git too old")
def test_partial_clone(script: PipTestEnvironment, tmp_path: pathlib.Path) -> None:
    """Test partial clone w/ a git-server that supports it"""
    repo_path = tmp_path / "repo"
    repo_file = _initialize_clonetest_server(
        repo_path, script, enable_partial_clone=True
    )
    clone_path1 = repo_path / "clone1"
    clone_path2 = repo_path / "clone2"

    commit = script.run("git", "rev-parse", "HEAD", cwd=str(repo_path)).stdout.strip()

    # Check that we can clone at HEAD
    Git().fetch_new(
        str(clone_path1),
        HiddenText(repo_path.as_uri(), redacted="*"),
        Git.make_rev_options(),
        verbosity=0,
    )
    # Check that we can clone to commit
    Git().fetch_new(
        str(clone_path2),
        HiddenText(repo_path.as_uri(), redacted="*"),
        Git.make_rev_options(commit),
        verbosity=0,
    )

    # Write some additional stuff to git pull
    repo_file.write_text("..")
    script.run("git", "commit", "-am", "second commit", cwd=str(repo_path))

    # Make sure git pull works - with server supporting filtering
    assert (
        "warning: filtering not recognized by server, ignoring"
        not in script.run("git", "pull", cwd=clone_path1).stderr
    )
    assert (
        "warning: filtering not recognized by server, ignoring"
        not in script.run("git", "pull", cwd=clone_path2).stderr
    )


@pytest.mark.skipif(Git().get_git_version() < (2, 17), reason="git too old")
def test_partial_clone_without_server_support(
    script: PipTestEnvironment, tmp_path: pathlib.Path
) -> None:
    """Test partial clone w/ a git-server that does not support it"""
    repo_path = tmp_path / "repo"
    repo_file = _initialize_clonetest_server(
        repo_path, script, enable_partial_clone=False
    )
    clone_path1 = repo_path / "clone1"
    clone_path2 = repo_path / "clone2"

    commit = script.run("git", "rev-parse", "HEAD", cwd=str(repo_path)).stdout.strip()

    # Check that we can clone at HEAD
    Git().fetch_new(
        str(clone_path1),
        HiddenText(repo_path.as_uri(), redacted="*"),
        Git.make_rev_options(),
        verbosity=0,
    )
    # Check that we can clone to commit
    Git().fetch_new(
        str(clone_path2),
        HiddenText(repo_path.as_uri(), redacted="*"),
        Git.make_rev_options(commit),
        verbosity=0,
    )

    # Write some additional stuff to git pull
    repo_file.write_text("..")
    script.run("git", "commit", "-am", "second commit", cwd=str(repo_path))

    # Make sure git pull works - even though server doesn't support filtering
    assert (
        "warning: filtering not recognized by server, ignoring"
        in script.run("git", "pull", cwd=clone_path1).stderr
    )
    assert (
        "warning: filtering not recognized by server, ignoring"
        in script.run("git", "pull", cwd=clone_path2).stderr
    )


def test_clone_without_partial_clone_support(
    script: PipTestEnvironment, tmp_path: pathlib.Path
) -> None:
    """Older git clients don't support partial clone. Test the fallback path"""
    repo_path = tmp_path / "repo"
    repo_file = _initialize_clonetest_server(
        repo_path, script, enable_partial_clone=True
    )
    clone_path = repo_path / "clone1"

    # Check that we can clone w/ old version of git w/o --filter
    with patch("pip._internal.vcs.git.Git.get_git_version", return_value=(2, 16)):
        Git().fetch_new(
            str(clone_path),
            HiddenText(repo_path.as_uri(), redacted="*"),
            Git.make_rev_options(),
            verbosity=0,
        )

    repo_file.write_text("...")
    script.run("git", "commit", "-am", "third commit", cwd=str(repo_path))

    # Should work fine w/o attempting to use `--filter` args
    assert (
        "warning: filtering not recognized by server, ignoring"
        not in script.run("git", "pull", cwd=clone_path).stderr
    )
