from pathlib import Path
from typing import Optional

import pytest

from tests.lib import (
    PipTestEnvironment,
    _change_test_package_version,
    _create_test_package,
    pyversion,  # noqa: F401
)
from tests.lib.git_submodule_helpers import (
    _change_test_package_submodule,
    _create_test_package_with_submodule,
    _pull_in_submodule_changes_to_module,
)
from tests.lib.local_repos import local_checkout


def _get_editable_repo_dir(script: PipTestEnvironment, package_name: str) -> Path:
    """
    Return the repository directory for an editable install.
    """
    return script.venv_path / "src" / package_name


def _get_editable_branch(script: PipTestEnvironment, package_name: str) -> str:
    """
    Return the current branch of an editable install.
    """
    repo_dir = _get_editable_repo_dir(script, package_name)
    result = script.run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=repo_dir)
    return result.stdout.strip()


def _get_branch_remote(
    script: PipTestEnvironment, package_name: str, branch: str
) -> str:
    """ """
    repo_dir = _get_editable_repo_dir(script, package_name)
    result = script.run("git", "config", f"branch.{branch}.remote", cwd=repo_dir)
    return result.stdout.strip()


def _github_checkout(
    url_path: str,
    tmpdir: Path,
    rev: Optional[str] = None,
    egg: Optional[str] = None,
    scheme: Optional[str] = None,
) -> str:
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
        scheme = "https"
    url = f"git+{scheme}://github.com/{url_path}"
    local_url = local_checkout(url, tmpdir)
    if rev is not None:
        local_url += f"@{rev}"
    if egg is not None:
        local_url += f"#egg={egg}"

    return local_url


def _make_version_pkg_url(
    path: Path, rev: Optional[str] = None, name: str = "version_pkg"
) -> str:
    """
    Return a "git+file://" URL to the version_pkg test package.

    Args:
      path: a pathlib.Path object pointing to a Git repository
        containing the version_pkg package.
      rev: an optional revision to install like a branch name, tag, or SHA.
    """
    file_url = path.as_uri()
    url_rev = "" if rev is None else f"@{rev}"
    url = f"git+{file_url}{url_rev}#egg={name}"

    return url


def _install_version_pkg_only(
    script: PipTestEnvironment,
    path: Path,
    rev: Optional[str] = None,
    allow_stderr_warning: bool = False,
) -> None:
    """
    Install the version_pkg package in editable mode (without returning
    the version).

    Args:
      path: a pathlib.Path object pointing to a Git repository
        containing the package.
      rev: an optional revision to install like a branch name or tag.
    """
    version_pkg_url = _make_version_pkg_url(path, rev=rev)
    script.pip(
        "install", "-e", version_pkg_url, allow_stderr_warning=allow_stderr_warning
    )


def _install_version_pkg(
    script: PipTestEnvironment,
    path: Path,
    rev: Optional[str] = None,
    allow_stderr_warning: bool = False,
) -> str:
    """
    Install the version_pkg package in editable mode, and return the version
    installed.

    Args:
      path: a pathlib.Path object pointing to a Git repository
        containing the package.
      rev: an optional revision to install like a branch name or tag.
    """
    _install_version_pkg_only(
        script,
        path,
        rev=rev,
        allow_stderr_warning=allow_stderr_warning,
    )
    result = script.run("version_pkg")
    version = result.stdout.strip()

    return version


def test_git_install_again_after_changes(script: PipTestEnvironment) -> None:
    """
    Test installing a repository a second time without specifying a revision,
    and after updates to the remote repository.

    This test also checks that no warning message like the following gets
    logged on the update: "Did not find branch or tag ..., assuming ref or
    revision."
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == "0.1"

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == "some different version"


def test_git_install_branch_again_after_branch_changes(
    script: PipTestEnvironment,
) -> None:
    """
    Test installing a branch again after the branch is updated in the remote
    repository.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    version = _install_version_pkg(script, version_pkg_path, rev="master")
    assert version == "0.1"

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev="master")
    assert version == "some different version"


@pytest.mark.network
def test_install_editable_from_git_with_https(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test cloning from Git with https.
    """
    url_path = "pypa/pip-test-package.git"
    local_url = _github_checkout(url_path, tmpdir, egg="pip-test-package")
    result = script.pip("install", "-e", local_url)
    result.assert_installed("pip-test-package", with_files=[".git"])


@pytest.mark.network
def test_install_noneditable_git(script: PipTestEnvironment) -> None:
    """
    Test installing from a non-editable git URL with a given tag.
    """
    result = script.pip(
        "install",
        "git+https://github.com/pypa/pip-test-package.git"
        "@0.1.1#egg=pip-test-package",
    )
    dist_info_folder = script.site_packages / "pip_test_package-0.1.1.dist-info"
    result.assert_installed("piptestpackage", without_egg_link=True, editable=False)
    result.did_create(dist_info_folder)


def test_git_with_sha1_revisions(script: PipTestEnvironment) -> None:
    """
    Git backend should be able to install from SHA1 revisions
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    _change_test_package_version(script, version_pkg_path)
    sha1 = script.run(
        "git",
        "rev-parse",
        "HEAD~1",
        cwd=version_pkg_path,
    ).stdout.strip()
    version = _install_version_pkg(script, version_pkg_path, rev=sha1)
    assert "0.1" == version


def test_git_with_short_sha1_revisions(script: PipTestEnvironment) -> None:
    """
    Git backend should be able to install from SHA1 revisions
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    _change_test_package_version(script, version_pkg_path)
    sha1 = script.run(
        "git",
        "rev-parse",
        "HEAD~1",
        cwd=version_pkg_path,
    ).stdout.strip()[:7]
    version = _install_version_pkg(
        script,
        version_pkg_path,
        rev=sha1,
        # WARNING: Did not find branch or tag ..., assuming revision or ref.
        allow_stderr_warning=True,
    )
    assert "0.1" == version


def test_git_with_branch_name_as_revision(script: PipTestEnvironment) -> None:
    """
    Git backend should be able to install from branch names
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    branch = "test_branch"
    script.run("git", "checkout", "-b", branch, cwd=version_pkg_path)
    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev=branch)
    assert "some different version" == version


def test_git_with_tag_name_as_revision(script: PipTestEnvironment) -> None:
    """
    Git backend should be able to install from tag names
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    script.run("git", "tag", "test_tag", cwd=version_pkg_path)
    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev="test_tag")
    assert "0.1" == version


def _add_ref(script: PipTestEnvironment, path: Path, ref: str) -> None:
    """
    Add a new ref to a repository at the given path.
    """
    script.run("git", "update-ref", ref, "HEAD", cwd=path)


def test_git_install_ref(script: PipTestEnvironment) -> None:
    """
    The Git backend should be able to install a ref with the first install.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    _add_ref(script, version_pkg_path, "refs/foo/bar")
    _change_test_package_version(script, version_pkg_path)

    version = _install_version_pkg(
        script,
        version_pkg_path,
        rev="refs/foo/bar",
        # WARNING: Did not find branch or tag ..., assuming revision or ref.
        allow_stderr_warning=True,
    )
    assert "0.1" == version


def test_git_install_then_install_ref(script: PipTestEnvironment) -> None:
    """
    The Git backend should be able to install a ref after a package has
    already been installed.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    _add_ref(script, version_pkg_path, "refs/foo/bar")
    _change_test_package_version(script, version_pkg_path)

    version = _install_version_pkg(script, version_pkg_path)
    assert "some different version" == version

    # Now install the ref.
    version = _install_version_pkg(
        script,
        version_pkg_path,
        rev="refs/foo/bar",
        # WARNING: Did not find branch or tag ..., assuming revision or ref.
        allow_stderr_warning=True,
    )
    assert "0.1" == version


@pytest.mark.network
@pytest.mark.parametrize(
    "rev, expected_sha",
    [
        # Clone the default branch
        ("", "5547fa909e83df8bd743d3978d6667497983a4b7"),
        # Clone a specific tag
        ("@0.1.1", "7d654e66c8fa7149c165ddeffa5b56bc06619458"),
        # Clone a specific commit
        (
            "@65cf0a5bdd906ecf48a0ac241c17d656d2071d56",
            "65cf0a5bdd906ecf48a0ac241c17d656d2071d56",
        ),
    ],
)
def test_install_git_logs_commit_sha(
    script: PipTestEnvironment, rev: str, expected_sha: str, tmpdir: Path
) -> None:
    """
    Test installing from a git repository logs a commit SHA.
    """
    url_path = "pypa/pip-test-package.git"
    base_local_url = _github_checkout(url_path, tmpdir)
    local_url = f"{base_local_url}{rev}#egg=pip-test-package"
    result = script.pip("install", local_url)
    # `[4:]` removes a 'git+' prefix
    assert f"Resolved {base_local_url[4:]} to commit {expected_sha}" in result.stdout


@pytest.mark.network
def test_git_with_tag_name_and_update(script: PipTestEnvironment, tmpdir: Path) -> None:
    """
    Test cloning a git repository and updating to a different version.
    """
    url_path = "pypa/pip-test-package.git"
    base_local_url = _github_checkout(url_path, tmpdir)

    local_url = f"{base_local_url}#egg=pip-test-package"
    result = script.pip("install", "-e", local_url)
    result.assert_installed("pip-test-package", with_files=[".git"])

    new_local_url = f"{base_local_url}@0.1.2#egg=pip-test-package"
    result = script.pip(
        "install",
        "--global-option=--version",
        "-e",
        new_local_url,
        allow_stderr_warning=True,
    )
    assert "0.1.2" in result.stdout


@pytest.mark.network
def test_git_branch_should_not_be_changed(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Editable installations should not change branch
    related to issue #32 and #161
    """
    url_path = "pypa/pip-test-package.git"
    local_url = _github_checkout(url_path, tmpdir, egg="pip-test-package")
    script.pip("install", "-e", local_url)
    branch = _get_editable_branch(script, "pip-test-package")
    assert "master" == branch


@pytest.mark.network
def test_git_with_non_editable_unpacking(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test cloning a git repository from a non-editable URL with a given tag.
    """
    url_path = "pypa/pip-test-package.git"
    local_url = _github_checkout(
        url_path,
        tmpdir,
        rev="0.1.2",
        egg="pip-test-package",
    )
    result = script.pip(
        "install",
        "--global-option=--quiet",
        local_url,
        allow_stderr_warning=True,
    )
    assert "0.1.2" in result.stdout


@pytest.mark.network
def test_git_with_editable_where_egg_contains_dev_string(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test cloning a git repository from an editable url which contains "dev"
    string
    """
    url_path = "dcramer/django-devserver.git"
    local_url = _github_checkout(
        url_path,
        tmpdir,
        egg="django-devserver",
        scheme="https",
    )
    result = script.pip("install", "-e", local_url)
    result.assert_installed("django-devserver", with_files=[".git"])


@pytest.mark.network
def test_git_with_non_editable_where_egg_contains_dev_string(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test cloning a git repository from a non-editable url which contains "dev"
    string
    """
    url_path = "dcramer/django-devserver.git"
    local_url = _github_checkout(
        url_path,
        tmpdir,
        egg="django-devserver",
        scheme="https",
    )
    result = script.pip("install", local_url)
    devserver_folder = script.site_packages / "devserver"
    result.did_create(devserver_folder)


def test_git_with_ambiguous_revs(script: PipTestEnvironment) -> None:
    """
    Test git with two "names" (tag/branch) pointing to the same commit
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    version_pkg_url = _make_version_pkg_url(version_pkg_path, rev="0.1")
    script.run("git", "tag", "0.1", cwd=version_pkg_path)
    result = script.pip("install", "-e", version_pkg_url)
    assert "Could not find a tag or branch" not in result.stdout
    # it is 'version-pkg' instead of 'version_pkg' because
    # egg-link name is version-pkg.egg-link because it is a single .py module
    result.assert_installed("version_pkg", with_files=[".git"])


def test_editable__no_revision(script: PipTestEnvironment) -> None:
    """
    Test a basic install in editable mode specifying no revision.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    _install_version_pkg_only(script, version_pkg_path)

    branch = _get_editable_branch(script, "version-pkg")
    assert branch == "master"

    remote = _get_branch_remote(script, "version-pkg", "master")
    assert remote == "origin"


def test_editable__branch_with_sha_same_as_default(script: PipTestEnvironment) -> None:
    """
    Test installing in editable mode a branch whose sha matches the sha
    of the default branch, but is different from the default branch.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    # Create a second branch with the same SHA.
    script.run("git", "branch", "develop", cwd=version_pkg_path)
    _install_version_pkg_only(script, version_pkg_path, rev="develop")

    branch = _get_editable_branch(script, "version-pkg")
    assert branch == "develop"

    remote = _get_branch_remote(script, "version-pkg", "develop")
    assert remote == "origin"


def test_editable__branch_with_sha_different_from_default(
    script: PipTestEnvironment,
) -> None:
    """
    Test installing in editable mode a branch whose sha is different from
    the sha of the default branch.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    # Create a second branch.
    script.run("git", "branch", "develop", cwd=version_pkg_path)
    # Add another commit to the master branch to give it a different sha.
    _change_test_package_version(script, version_pkg_path)

    version = _install_version_pkg(script, version_pkg_path, rev="develop")
    assert version == "0.1"

    branch = _get_editable_branch(script, "version-pkg")
    assert branch == "develop"

    remote = _get_branch_remote(script, "version-pkg", "develop")
    assert remote == "origin"


def test_editable__non_master_default_branch(script: PipTestEnvironment) -> None:
    """
    Test the branch you get after an editable install from a remote repo
    with a non-master default branch.
    """
    version_pkg_path = _create_test_package(script.scratch_path)
    # Change the default branch of the remote repo to a name that is
    # alphabetically after "master".
    script.run("git", "checkout", "-b", "release", cwd=version_pkg_path)
    _install_version_pkg_only(script, version_pkg_path)

    branch = _get_editable_branch(script, "version-pkg")
    assert branch == "release"


def test_reinstalling_works_with_editable_non_master_branch(
    script: PipTestEnvironment,
) -> None:
    """
    Reinstalling an editable installation should not assume that the "master"
    branch exists. See https://github.com/pypa/pip/issues/4448.
    """
    version_pkg_path = _create_test_package(script.scratch_path)

    # Switch the default branch to something other than 'master'
    script.run("git", "branch", "-m", "foobar", cwd=version_pkg_path)

    version = _install_version_pkg(script, version_pkg_path)
    assert "0.1" == version

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert "some different version" == version


# TODO(pnasrat) fix all helpers to do right things with paths on windows.
@pytest.mark.skipif("sys.platform == 'win32'")
@pytest.mark.xfail(
    condition=True,
    reason="Git submodule against file: is not working; waiting for a good solution",
    run=True,
)
def test_check_submodule_addition(script: PipTestEnvironment) -> None:
    """
    Submodules are pulled in on install and updated on upgrade.
    """
    module_path, submodule_path = _create_test_package_with_submodule(
        script, rel_path="testpkg/static"
    )

    install_result = script.pip(
        "install", "-e", f"git+{module_path.as_uri()}#egg=version_pkg"
    )
    install_result.did_create(script.venv / "src/version-pkg/testpkg/static/testfile")

    _change_test_package_submodule(script, submodule_path)
    _pull_in_submodule_changes_to_module(
        script,
        module_path,
        rel_path="testpkg/static",
    )

    # expect error because git may write to stderr
    update_result = script.pip(
        "install",
        "-e",
        f"git+{module_path.as_uri()}#egg=version_pkg",
        "--upgrade",
    )

    update_result.did_create(script.venv / "src/version-pkg/testpkg/static/testfile2")


def test_install_git_branch_not_cached(script: PipTestEnvironment) -> None:
    """
    Installing git urls with a branch revision does not cause wheel caching.
    """
    PKG = "gitbranchnotcached"
    repo_dir = _create_test_package(script.scratch_path, name=PKG)
    url = _make_version_pkg_url(repo_dir, rev="master", name=PKG)
    result = script.pip("install", url, "--only-binary=:all:")
    assert f"Successfully built {PKG}" in result.stdout, result.stdout
    script.pip("uninstall", "-y", PKG)
    # build occurs on the second install too because it is not cached
    result = script.pip("install", url)
    assert f"Successfully built {PKG}" in result.stdout, result.stdout


def test_install_git_sha_cached(script: PipTestEnvironment) -> None:
    """
    Installing git urls with a sha revision does cause wheel caching.
    """
    PKG = "gitshacached"
    repo_dir = _create_test_package(script.scratch_path, name=PKG)
    commit = script.run("git", "rev-parse", "HEAD", cwd=repo_dir).stdout.strip()
    url = _make_version_pkg_url(repo_dir, rev=commit, name=PKG)
    result = script.pip("install", url)
    assert f"Successfully built {PKG}" in result.stdout, result.stdout
    script.pip("uninstall", "-y", PKG)
    # build does not occur on the second install because it is cached
    result = script.pip("install", url)
    assert f"Successfully built {PKG}" not in result.stdout, result.stdout
