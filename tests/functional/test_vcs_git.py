"""
Contains functional tests of the Git class.
"""

from pip.utils.temp_dir import TempDirectory
from pip.vcs.git import Git


def get_head_sha(script, dest):
    """
    Return the HEAD sha.
    """
    result = script.run('git', 'rev-parse', 'HEAD', cwd=dest)
    sha = result.stdout.strip()
    return sha


def do_commit(script, dest):
    script.run(
        'git', 'commit', '-q', '--author', 'pip <pypa-dev@googlegroups.com>',
        '--allow-empty', '-m', 'test commit', cwd=dest
    )
    sha = get_head_sha(script, dest)

    return sha


def add_commits(script, dest, count):
    """
    Return a list of the commit hashes from oldest to newest.
    """
    shas = []
    for index in range(count):
        sha = do_commit(script, dest)
        shas.append(sha)

    return shas


def check_rev(repo_dir, rev, expected_sha):
    git = Git()
    assert git.get_revision_sha(repo_dir, rev) == expected_sha


def test_get_revision_sha(script):
    with TempDirectory(kind="testing") as temp:
        repo_dir = temp.path
        script.run('git', 'init', cwd=repo_dir)
        shas = add_commits(script, repo_dir, count=6)

        local_branch_sha = shas[0]
        tag_sha = shas[1]
        origin_branch_sha = shas[2]
        upstream_branch_sha = shas[3]
        ref_sha = shas[4]
        head_sha = shas[5]
        assert head_sha == shas[-1]

        script.run(
            'git', 'branch', 'local-branch', local_branch_sha, cwd=repo_dir
        )
        script.run('git', 'tag', 'v1.0', tag_sha, cwd=repo_dir)
        script.run(
            'git', 'update-ref', 'refs/remotes/origin/origin-branch',
            origin_branch_sha, cwd=repo_dir
        )
        script.run(
            'git', 'update-ref', 'refs/remotes/upstream/upstream-branch',
            upstream_branch_sha, cwd=repo_dir
        )
        script.run(
            'git', 'update-ref', 'refs/generic-ref', ref_sha, cwd=repo_dir
        )

        # Test two tags pointing to the same sha.
        script.run('git', 'tag', 'v2.0', tag_sha, cwd=repo_dir)
        # Test tags sharing the same suffix as another tag, both before and
        # after alphabetically.
        script.run('git', 'tag', 'aaa/v1.0', head_sha, cwd=repo_dir)
        script.run('git', 'tag', 'zzz/v1.0', head_sha, cwd=repo_dir)

        check_rev(repo_dir, 'local-branch', None)
        check_rev(repo_dir, 'v1.0', tag_sha)
        check_rev(repo_dir, 'v2.0', tag_sha)
        check_rev(repo_dir, 'origin-branch', origin_branch_sha)
        check_rev(repo_dir, 'upstream-branch', None)
        check_rev(repo_dir, 'generic-ref', None)
        # Test passing a valid commit hash.
        check_rev(repo_dir, tag_sha, None)
        # Test passing a non-existent name.
        check_rev(repo_dir, 'does-not-exist', None)
