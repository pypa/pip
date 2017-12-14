import pytest
from mock import patch

from pip._internal.vcs.git import Git
from tests.lib import _create_test_package
from tests.lib.git_submodule_helpers import (
    _change_test_package_submodule, _create_test_package_with_submodule,
    _pull_in_submodule_changes_to_module,
)


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


@patch('pip._internal.vcs.git.Git.get_revision_sha')
def test_check_rev_options_ref_exists(get_sha_mock):
    get_sha_mock.return_value = '123456'
    git = Git()
    rev_options = git.make_rev_options('develop')

    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == '123456'


@patch('pip._internal.vcs.git.Git.get_revision_sha')
def test_check_rev_options_ref_not_found(get_sha_mock):
    get_sha_mock.return_value = None
    git = Git()
    rev_options = git.make_rev_options('develop')

    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == 'develop'


@patch('pip._internal.vcs.git.Git.get_revision_sha')
def test_check_rev_options_not_found_warning(get_sha_mock, caplog):
    get_sha_mock.return_value = None
    git = Git()

    sha = 40 * 'a'
    rev_options = git.make_rev_options(sha)
    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == sha

    rev_options = git.make_rev_options(sha[:6])
    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == 'aaaaaa'

    # Check that a warning got logged only for the abbreviated hash.
    messages = [r.getMessage() for r in caplog.records]
    messages = [msg for msg in messages if msg.startswith('Did not find ')]
    assert messages == [
        "Did not find branch or tag 'aaaaaa', assuming revision or ref."
    ]


# TODO(pnasrat) fix all helpers to do right things with paths on windows.
@pytest.mark.skipif("sys.platform == 'win32'")
@pytest.mark.network
def test_check_submodule_addition(script):
    """
    Submodules are pulled in on install and updated on upgrade.
    """
    module_path, submodule_path = _create_test_package_with_submodule(script)

    install_result = script.pip(
        'install', '-e', 'git+' + module_path + '#egg=version_pkg'
    )
    assert (
        script.venv / 'src/version-pkg/testpkg/static/testfile'
        in install_result.files_created
    )

    _change_test_package_submodule(script, submodule_path)
    _pull_in_submodule_changes_to_module(script, module_path)

    # expect error because git may write to stderr
    update_result = script.pip(
        'install', '-e', 'git+' + module_path + '#egg=version_pkg',
        '--upgrade',
        expect_error=True,
    )

    assert (
        script.venv / 'src/version-pkg/testpkg/static/testfile2'
        in update_result.files_created
    )
