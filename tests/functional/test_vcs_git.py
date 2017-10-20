"""
Contains functional tests of the Git class.
"""

from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.vcs.git import Git


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
