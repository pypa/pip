"""
Contains functional tests of the Git class.
"""

import os

import pytest

from pip._internal.vcs.git import Git, RemoteNotFoundError
from tests.lib import _create_test_package, _git_commit, _test_path_to_file_url


def get_head_sha(script, dest):
    """Return the HEAD sha."""
    result = script.run('git', 'rev-parse', 'HEAD', cwd=dest)
    sha = result.stdout.strip()

    return sha


def checkout_ref(script, repo_dir, ref):
    script.run('git', 'checkout', ref, cwd=repo_dir, expect_stderr=True)


def checkout_new_branch(script, repo_dir, branch):
    script.run(
        'git', 'checkout', '-b', branch, cwd=repo_dir, expect_stderr=True,
    )


def do_commit(script, dest):
    _git_commit(script, dest, message='test commit', args=['--allow-empty'])
    return get_head_sha(script, dest)


def add_commits(script, dest, count):
    """Return a list of the commit hashes from oldest to newest."""
    shas = []
    for index in range(count):
        sha = do_commit(script, dest)
        shas.append(sha)

    return shas


def check_rev(repo_dir, rev, expected):
    git = Git()
    assert git.get_revision_sha(repo_dir, rev) == expected


def test_git_dir_ignored(tmpdir):
    """
    Test that a GIT_DIR environment variable is ignored.
    """
    repo_path = tmpdir / 'test-repo'
    repo_path.mkdir()
    repo_dir = str(repo_path)

    env = {'GIT_DIR': 'foo'}
    # If GIT_DIR is not ignored, then os.listdir() will return ['foo'].
    Git().run_command(['init', repo_dir], cwd=repo_dir, extra_environ=env)
    assert os.listdir(repo_dir) == ['.git']


def test_git_work_tree_ignored(tmpdir):
    """
    Test that a GIT_WORK_TREE environment variable is ignored.
    """
    repo_path = tmpdir / 'test-repo'
    repo_path.mkdir()
    repo_dir = str(repo_path)

    git = Git()
    git.run_command(['init', repo_dir], cwd=repo_dir)
    # Choose a directory relative to the cwd that does not exist.
    # If GIT_WORK_TREE is not ignored, then the command will error out
    # with: "fatal: This operation must be run in a work tree".
    env = {'GIT_WORK_TREE': 'foo'}
    git.run_command(['status', repo_dir], extra_environ=env, cwd=repo_dir)


def test_get_remote_url(script, tmpdir):
    source_dir = tmpdir / 'source'
    source_dir.mkdir()
    source_url = _test_path_to_file_url(source_dir)

    source_dir = str(source_dir)
    script.run('git', 'init', cwd=source_dir)
    do_commit(script, source_dir)

    repo_dir = str(tmpdir / 'repo')
    script.run('git', 'clone', source_url, repo_dir, expect_stderr=True)

    remote_url = Git().get_remote_url(repo_dir)
    assert remote_url == source_url


def test_get_remote_url__no_remote(script, tmpdir):
    """
    Test a repo with no remote.
    """
    repo_dir = tmpdir / 'temp-repo'
    repo_dir.mkdir()
    repo_dir = str(repo_dir)

    script.run('git', 'init', cwd=repo_dir)

    with pytest.raises(RemoteNotFoundError):
        Git().get_remote_url(repo_dir)


def test_get_current_branch(script):
    repo_dir = str(script.scratch_path)

    script.run('git', 'init', cwd=repo_dir)
    sha = do_commit(script, repo_dir)

    git = Git()
    assert git.get_current_branch(repo_dir) == 'master'

    # Switch to a branch with the same SHA as "master" but whose name
    # is alphabetically after.
    checkout_new_branch(script, repo_dir, 'release')
    assert git.get_current_branch(repo_dir) == 'release'

    # Also test the detached HEAD case.
    checkout_ref(script, repo_dir, sha)
    assert git.get_current_branch(repo_dir) is None


def test_get_current_branch__branch_and_tag_same_name(script, tmpdir):
    """
    Check calling get_current_branch() from a branch or tag when the branch
    and tag have the same name.
    """
    repo_dir = str(tmpdir)
    script.run('git', 'init', cwd=repo_dir)
    do_commit(script, repo_dir)
    checkout_new_branch(script, repo_dir, 'dev')
    # Create a tag with the same name as the branch.
    script.run('git', 'tag', 'dev', cwd=repo_dir)

    git = Git()
    assert git.get_current_branch(repo_dir) == 'dev'

    # Now try with the tag checked out.
    checkout_ref(script, repo_dir, 'refs/tags/dev')
    assert git.get_current_branch(repo_dir) is None


def test_get_revision_sha(script):
    repo_dir = str(script.scratch_path)

    script.run('git', 'init', cwd=repo_dir)
    shas = add_commits(script, repo_dir, count=3)

    tag_sha = shas[0]
    origin_sha = shas[1]
    head_sha = shas[2]
    assert head_sha == shas[-1]

    origin_ref = 'refs/remotes/origin/origin-branch'
    generic_ref = 'refs/generic-ref'

    script.run(
        'git', 'branch', 'local-branch', head_sha, cwd=repo_dir
    )
    script.run('git', 'tag', 'v1.0', tag_sha, cwd=repo_dir)
    script.run('git', 'update-ref', origin_ref, origin_sha, cwd=repo_dir)
    script.run(
        'git', 'update-ref', 'refs/remotes/upstream/upstream-branch',
        head_sha, cwd=repo_dir
    )
    script.run('git', 'update-ref', generic_ref, head_sha, cwd=repo_dir)

    # Test two tags pointing to the same sha.
    script.run('git', 'tag', 'v2.0', tag_sha, cwd=repo_dir)
    # Test tags sharing the same suffix as another tag, both before and
    # after the suffix alphabetically.
    script.run('git', 'tag', 'aaa/v1.0', head_sha, cwd=repo_dir)
    script.run('git', 'tag', 'zzz/v1.0', head_sha, cwd=repo_dir)

    check_rev(repo_dir, 'v1.0', (tag_sha, False))
    check_rev(repo_dir, 'v2.0', (tag_sha, False))
    check_rev(repo_dir, 'origin-branch', (origin_sha, True))

    ignored_names = [
        # Local branches should be ignored.
        'local-branch',
        # Non-origin remote branches should be ignored.
        'upstream-branch',
        # Generic refs should be ignored.
        'generic-ref',
        # Fully spelled-out refs should be ignored.
        origin_ref,
        generic_ref,
        # Test passing a valid commit hash.
        tag_sha,
        # Test passing a non-existent name.
        'does-not-exist',
    ]
    for name in ignored_names:
        check_rev(repo_dir, name, (None, False))


def test_is_commit_id_equal(script):
    """
    Test Git.is_commit_id_equal().
    """
    version_pkg_path = _create_test_package(script)
    script.run('git', 'branch', 'branch0.1', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    assert git.is_commit_id_equal(version_pkg_path, commit)
    assert not git.is_commit_id_equal(version_pkg_path, commit[:7])
    assert not git.is_commit_id_equal(version_pkg_path, 'branch0.1')
    assert not git.is_commit_id_equal(version_pkg_path, 'abc123')
    # Also check passing a None value.
    assert not git.is_commit_id_equal(version_pkg_path, None)
