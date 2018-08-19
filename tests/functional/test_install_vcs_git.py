import pytest

from tests.lib import (
    _change_test_package_version, _create_test_package, pyversion,
)
from tests.lib.git_submodule_helpers import (
    _change_test_package_submodule, _create_test_package_with_submodule,
    _pull_in_submodule_changes_to_module,
)
from tests.lib.local_repos import local_checkout


def _github_checkout(url_path, temp_dir, egg=None, scheme=None):
    """
    Call local_checkout() with a GitHub URL, and return the resulting URL.

    Args:
      url_path: the string used to create the package URL by filling in the
        format string "git+{scheme}://github.com/{url_path}".
      temp_dir: the pytest tmpdir value.
      egg: an optional project name to append to the URL as the egg fragment,
        prior to returning.
      scheme: the scheme without the "git+" prefix. Defaults to "https".
    """
    if scheme is None:
        scheme = 'https'
    url = 'git+{}://github.com/{}'.format(scheme, url_path)
    local_url = local_checkout(url, temp_dir.join('cache'))
    if egg is not None:
        local_url += '#egg={}'.format(egg)

    return local_url


def _make_version_pkg_url(path, rev=None):
    """
    Return a "git+file://" URL to the version_pkg test package.

    Args:
      path: a tests.lib.path.Path object pointing to a Git repository
        containing the version_pkg package.
      rev: an optional revision to install like a branch name, tag, or SHA.
    """
    path = path.abspath.replace('\\', '/')
    url_rev = '' if rev is None else '@{}'.format(rev)
    url = 'git+file://{}{}#egg=version_pkg'.format(path, url_rev)

    return url


def _install_version_pkg(script, path, rev=None, expect_stderr=False):
    """
    Install the version_pkg package, and return the version installed.

    Args:
      path: a tests.lib.path.Path object pointing to a Git repository
        containing the package.
      rev: an optional revision to install like a branch name or tag.
    """
    version_pkg_url = _make_version_pkg_url(path, rev=rev)
    script.pip('install', '-e', version_pkg_url, expect_stderr=expect_stderr)
    result = script.run('version_pkg')
    version = result.stdout.strip()

    return version


def test_git_install_again_after_changes(script):
    """
    Test installing a repository a second time without specifying a revision,
    and after updates to the remote repository.

    This test also checks that no warning message like the following gets
    logged on the update: "Did not find branch or tag ..., assuming ref or
    revision."
    """
    version_pkg_path = _create_test_package(script)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == '0.1'

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == 'some different version'


def test_git_install_branch_again_after_branch_changes(script):
    """
    Test installing a branch again after the branch is updated in the remote
    repository.
    """
    version_pkg_path = _create_test_package(script)
    version = _install_version_pkg(script, version_pkg_path, rev='master')
    assert version == '0.1'

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev='master')
    assert version == 'some different version'


@pytest.mark.network
def test_install_editable_from_git_with_https(script, tmpdir):
    """
    Test cloning from Git with https.
    """
    url_path = 'pypa/pip-test-package.git'
    local_url = _github_checkout(url_path, tmpdir, egg='pip-test-package')
    result = script.pip('install', '-e', local_url, expect_error=True)
    result.assert_installed('pip-test-package', with_files=['.git'])


@pytest.mark.network
def test_install_noneditable_git(script, tmpdir):
    """
    Test installing from a non-editable git URL with a given tag.
    """
    result = script.pip(
        'install',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1.1#egg=pip-test-package'
    )
    egg_info_folder = (
        script.site_packages /
        'pip_test_package-0.1.1-py%s.egg-info' % pyversion
    )
    result.assert_installed('piptestpackage',
                            without_egg_link=True,
                            editable=False)
    assert egg_info_folder in result.files_created, str(result)


def test_git_with_sha1_revisions(script):
    """
    Git backend should be able to install from SHA1 revisions
    """
    version_pkg_path = _create_test_package(script)
    _change_test_package_version(script, version_pkg_path)
    sha1 = script.run(
        'git', 'rev-parse', 'HEAD~1',
        cwd=version_pkg_path,
    ).stdout.strip()
    version = _install_version_pkg(
        script, version_pkg_path, rev=sha1, expect_stderr=True,
    )
    assert '0.1' == version


def test_git_with_short_sha1_revisions(script):
    """
    Git backend should be able to install from SHA1 revisions
    """
    version_pkg_path = _create_test_package(script)
    _change_test_package_version(script, version_pkg_path)
    sha1 = script.run(
        'git', 'rev-parse', 'HEAD~1',
        cwd=version_pkg_path,
    ).stdout.strip()[:7]
    version = _install_version_pkg(
        script, version_pkg_path, rev=sha1, expect_stderr=True,
    )
    assert '0.1' == version


def test_git_with_branch_name_as_revision(script):
    """
    Git backend should be able to install from branch names
    """
    version_pkg_path = _create_test_package(script)
    branch = 'test_branch'
    script.run(
        'git', 'checkout', '-b', branch,
        expect_stderr=True,
        cwd=version_pkg_path,
    )
    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev=branch)
    assert 'some different version' == version


def test_git_with_tag_name_as_revision(script):
    """
    Git backend should be able to install from tag names
    """
    version_pkg_path = _create_test_package(script)
    script.run(
        'git', 'tag', 'test_tag',
        expect_stderr=True,
        cwd=version_pkg_path,
    )
    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev='test_tag')
    assert '0.1' == version


def _add_ref(script, path, ref):
    """
    Add a new ref to a repository at the given path.
    """
    script.run('git', 'update-ref', ref, 'HEAD', expect_stderr=True, cwd=path)


def test_git_install_ref(script):
    """
    The Git backend should be able to install a ref with the first install.
    """
    version_pkg_path = _create_test_package(script)
    _add_ref(script, version_pkg_path, 'refs/foo/bar')
    _change_test_package_version(script, version_pkg_path)

    version = _install_version_pkg(
        script, version_pkg_path, rev='refs/foo/bar', expect_stderr=True,
    )
    assert '0.1' == version


def test_git_install_then_install_ref(script):
    """
    The Git backend should be able to install a ref after a package has
    already been installed.
    """
    version_pkg_path = _create_test_package(script)
    _add_ref(script, version_pkg_path, 'refs/foo/bar')
    _change_test_package_version(script, version_pkg_path)

    version = _install_version_pkg(
        script, version_pkg_path, expect_stderr=True,
    )
    assert 'some different version' == version

    # Now install the ref.
    version = _install_version_pkg(
        script, version_pkg_path, rev='refs/foo/bar', expect_stderr=True,
    )
    assert '0.1' == version


@pytest.mark.network
def test_git_with_tag_name_and_update(script, tmpdir):
    """
    Test cloning a git repository and updating to a different version.
    """
    url_path = 'pypa/pip-test-package.git'
    local_url = _github_checkout(url_path, tmpdir, egg='pip-test-package')
    result = script.pip('install', '-e', local_url, expect_error=True)
    result.assert_installed('pip-test-package', with_files=['.git'])

    new_local_url = _github_checkout(url_path, tmpdir)
    new_local_url += '@0.1.2#egg=pip-test-package'
    result = script.pip(
        'install', '--global-option=--version', '-e', new_local_url,
        expect_error=True,
    )
    assert '0.1.2' in result.stdout


@pytest.mark.network
def test_git_branch_should_not_be_changed(script, tmpdir):
    """
    Editable installations should not change branch
    related to issue #32 and #161
    """
    url_path = 'pypa/pip-test-package.git'
    local_url = _github_checkout(url_path, tmpdir, egg='pip-test-package')
    script.pip('install', '-e', local_url, expect_error=True)
    source_dir = script.venv_path / 'src' / 'pip-test-package'
    result = script.run('git', 'branch', cwd=source_dir)
    assert '* master' in result.stdout, result.stdout


@pytest.mark.network
def test_git_with_non_editable_unpacking(script, tmpdir):
    """
    Test cloning a git repository from a non-editable URL with a given tag.
    """
    url_path = 'pypa/pip-test-package.git@0.1.2#egg=pip-test-package'
    local_url = _github_checkout(url_path, tmpdir)
    result = script.pip(
        'install', '--global-option=--version', local_url, expect_error=True,
    )
    assert '0.1.2' in result.stdout


@pytest.mark.network
def test_git_with_editable_where_egg_contains_dev_string(script, tmpdir):
    """
    Test cloning a git repository from an editable url which contains "dev"
    string
    """
    url_path = 'dcramer/django-devserver.git'
    local_url = _github_checkout(
        url_path, tmpdir, egg='django-devserver', scheme='git',
    )
    result = script.pip('install', '-e', local_url)
    result.assert_installed('django-devserver', with_files=['.git'])


@pytest.mark.network
def test_git_with_non_editable_where_egg_contains_dev_string(script, tmpdir):
    """
    Test cloning a git repository from a non-editable url which contains "dev"
    string
    """
    url_path = 'dcramer/django-devserver.git'
    local_url = _github_checkout(
        url_path, tmpdir, egg='django-devserver', scheme='git',
    )
    result = script.pip('install', local_url)
    devserver_folder = script.site_packages / 'devserver'
    assert devserver_folder in result.files_created, str(result)


def test_git_with_ambiguous_revs(script):
    """
    Test git with two "names" (tag/branch) pointing to the same commit
    """
    version_pkg_path = _create_test_package(script)
    version_pkg_url = _make_version_pkg_url(version_pkg_path, rev='0.1')
    script.run('git', 'tag', '0.1', cwd=version_pkg_path)
    result = script.pip('install', '-e', version_pkg_url)
    assert 'Could not find a tag or branch' not in result.stdout
    # it is 'version-pkg' instead of 'version_pkg' because
    # egg-link name is version-pkg.egg-link because it is a single .py module
    result.assert_installed('version-pkg', with_files=['.git'])


def test_git_works_with_editable_non_origin_repo(script):
    # set up, create a git repo and install it as editable from a local
    # directory path
    version_pkg_path = _create_test_package(script)
    script.pip('install', '-e', version_pkg_path.abspath)

    # 'freeze'ing this should not fall over, but should result in stderr output
    # warning
    result = script.pip('freeze', expect_stderr=True)
    assert "Error when trying to get requirement" in result.stderr
    assert "Could not determine repository location" in result.stdout
    assert "version-pkg==0.1" in result.stdout


def test_reinstalling_works_with_editible_non_master_branch(script):
    """
    Reinstalling an editable installation should not assume that the "master"
    branch exists. See https://github.com/pypa/pip/issues/4448.
    """
    version_pkg_path = _create_test_package(script)

    # Switch the default branch to something other than 'master'
    script.run('git', 'branch', '-m', 'foobar', cwd=version_pkg_path)

    version = _install_version_pkg(script, version_pkg_path)
    assert '0.1' == version

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert 'some different version' == version


# TODO(pnasrat) fix all helpers to do right things with paths on windows.
@pytest.mark.skipif("sys.platform == 'win32'")
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
