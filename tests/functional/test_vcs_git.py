"""
Contains functional tests of the Git class.
"""

import os

import pytest

from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.vcs.git import Git
from tests.lib import _create_test_package


def get_head_sha(script, dest):
    """Return the HEAD sha."""
    result = script.run('git', 'rev-parse', 'HEAD', cwd=dest)
    sha = result.stdout.strip()

    return sha


def do_commit(script, dest):
    script.run(
        'git', 'commit', '-q', '--author', 'pip <pypa-dev@googlegroups.com>',
        '--allow-empty', '-m', 'test commit', cwd=dest
    )
    return get_head_sha(script, dest)


def add_commits(script, dest, count):
    """Return a list of the commit hashes from oldest to newest."""
    shas = []
    for index in range(count):
        sha = do_commit(script, dest)
        shas.append(sha)

    return shas


def check_rev(repo_dir, rev, expected_sha):
    git = Git()
    assert git.get_revision_sha(repo_dir, rev) == expected_sha


def test_git_dir_ignored():
    """
    Test that a GIT_DIR environment variable is ignored.
    """
    git = Git()
    with TempDirectory() as temp:
        temp_dir = temp.path
        env = {'GIT_DIR': 'foo'}
        # If GIT_DIR is not ignored, then os.listdir() will return ['foo'].
        git.run_command(['init', temp_dir], cwd=temp_dir, extra_environ=env)
        assert os.listdir(temp_dir) == ['.git']


def test_git_work_tree_ignored():
    """
    Test that a GIT_WORK_TREE environment variable is ignored.
    """
    git = Git()
    with TempDirectory() as temp:
        temp_dir = temp.path
        git.run_command(['init', temp_dir], cwd=temp_dir)
        # Choose a directory relative to the cwd that does not exist.
        # If GIT_WORK_TREE is not ignored, then the command will error out
        # with: "fatal: This operation must be run in a work tree".
        env = {'GIT_WORK_TREE': 'foo'}
        git.run_command(['status', temp_dir], extra_environ=env, cwd=temp_dir)


def test_get_revision_sha(script):
    with TempDirectory(kind="testing") as temp:
        repo_dir = temp.path
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

        check_rev(repo_dir, 'v1.0', tag_sha)
        check_rev(repo_dir, 'v2.0', tag_sha)
        check_rev(repo_dir, 'origin-branch', origin_sha)

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
            check_rev(repo_dir, name, None)


@pytest.mark.network
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
