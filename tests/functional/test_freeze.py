import os
import re
import sys
import textwrap
from doctest import ELLIPSIS, OutputChecker

import pytest
from pip._vendor.packaging.utils import canonicalize_name

from tests.lib import (
    _create_test_package,
    _create_test_package_with_srcdir,
    _git_commit,
    _vcs_add,
    create_test_package_with_setup,
    need_bzr,
    need_mercurial,
    need_svn,
    path_to_url,
    wheel,
)

distribute_re = re.compile("^distribute==[0-9.]+\n", re.MULTILINE)


def _check_output(result, expected):
    checker = OutputChecker()
    actual = str(result)

    # FIXME!  The following is a TOTAL hack.  For some reason the
    # __str__ result for pkg_resources.Requirement gets downcased on
    # Windows.  Since INITools is the only package we're installing
    # in this file with funky case requirements, I'm forcibly
    # upcasing it.  You can also normalize everything to lowercase,
    # but then you have to remember to upcase <BLANKLINE>.  The right
    # thing to do in the end is probably to find out how to report
    # the proper fully-cased package name in our error message.
    if sys.platform == "win32":
        actual = actual.replace("initools", "INITools")

    # This allows our existing tests to work when run in a context
    # with distribute installed.
    actual = distribute_re.sub("", actual)

    def banner(msg):
        return f"\n========== {msg} ==========\n"

    assert checker.check_output(expected, actual, ELLIPSIS), (
        banner("EXPECTED") + expected + banner("ACTUAL") + actual + banner(6 * "=")
    )


def test_basic_freeze(script):
    """
    Some tests of freeze, first we have to install some stuff.  Note that
    the test is a little crude at the end because Python 2.5+ adds egg
    info to the standard library, so stuff like wsgiref will show up in
    the freezing.  (Probably that should be accounted for in pip, but
    currently it is not).

    """
    script.scratch_path.joinpath("initools-req.txt").write_text(
        textwrap.dedent(
            """\
        simple==2.0
        # and something else to test out:
        simple2<=3.0
        """
        )
    )
    script.pip_install_local(
        "-r",
        script.scratch_path / "initools-req.txt",
    )
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """\
        ...simple==2.0
        simple2==3.0...
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)


def test_freeze_with_pip(script):
    """Test pip shows itself"""
    result = script.pip("freeze", "--all")
    assert "pip==" in result.stdout


def test_exclude_and_normalization(script, tmpdir):
    req_path = wheel.make_wheel(name="Normalizable_Name", version="1.0").save_to_dir(
        tmpdir
    )
    script.pip("install", "--no-index", req_path)
    result = script.pip("freeze")
    assert "Normalizable_Name" in result.stdout
    result = script.pip("freeze", "--exclude", "normalizablE-namE")
    assert "Normalizable_Name" not in result.stdout


def test_freeze_multiple_exclude_with_all(script, with_wheel):
    result = script.pip("freeze", "--all")
    assert "pip==" in result.stdout
    assert "wheel==" in result.stdout
    result = script.pip("freeze", "--all", "--exclude", "pip", "--exclude", "wheel")
    assert "pip==" not in result.stdout
    assert "wheel==" not in result.stdout


def test_freeze_with_invalid_names(script):
    """
    Test that invalid names produce warnings and are passed over gracefully.
    """

    def fake_install(pkgname, dest):
        egg_info_path = os.path.join(
            dest,
            "{}-1.0-py{}.{}.egg-info".format(
                pkgname.replace("-", "_"), sys.version_info[0], sys.version_info[1]
            ),
        )
        with open(egg_info_path, "w") as egg_info_file:
            egg_info_file.write(
                textwrap.dedent(
                    """\
                Metadata-Version: 1.0
                Name: {}
                Version: 1.0
                """.format(
                        pkgname
                    )
                )
            )

    valid_pkgnames = ("middle-dash", "middle_underscore", "middle.dot")
    invalid_pkgnames = (
        "-leadingdash",
        "_leadingunderscore",
        ".leadingdot",
        "trailingdash-",
        "trailingunderscore_",
        "trailingdot.",
    )
    for pkgname in valid_pkgnames + invalid_pkgnames:
        fake_install(pkgname, script.site_packages_path)

    result = script.pip("freeze", expect_stderr=True)

    # Check all valid names are in the output.
    output_lines = {line.strip() for line in result.stdout.splitlines()}
    for name in valid_pkgnames:
        assert f"{name}==1.0" in output_lines

    # Check all invalid names are excluded from the output.
    canonical_invalid_names = {canonicalize_name(n) for n in invalid_pkgnames}
    for line in output_lines:
        output_name, _, _ = line.partition("=")
        assert canonicalize_name(output_name) not in canonical_invalid_names

    # The invalid names should be logged.
    for name in canonical_invalid_names:
        assert f"Ignoring invalid distribution {name} (" in result.stderr


@pytest.mark.git
def test_freeze_editable_not_vcs(script, tmpdir):
    """
    Test an editable install that is not version controlled.
    """
    pkg_path = _create_test_package(script)
    # Rename the .git directory so the directory is no longer recognized
    # as a VCS directory.
    os.rename(os.path.join(pkg_path, ".git"), os.path.join(pkg_path, ".bak"))
    script.pip("install", "-e", pkg_path)
    result = script.pip("freeze")

    # We need to apply os.path.normcase() to the path since that is what
    # the freeze code does.
    expected = textwrap.dedent(
        """\
    ...# Editable install with no version control (version-pkg==0.1)
    -e {}
    ...""".format(
            os.path.normcase(pkg_path)
        )
    )
    _check_output(result.stdout, expected)


@pytest.mark.git
def test_freeze_editable_git_with_no_remote(script, tmpdir, deprecated_python):
    """
    Test an editable Git install with no remote url.
    """
    pkg_path = _create_test_package(script)
    script.pip("install", "-e", pkg_path)
    result = script.pip("freeze")

    if not deprecated_python:
        assert result.stderr == ""

    # We need to apply os.path.normcase() to the path since that is what
    # the freeze code does.
    expected = textwrap.dedent(
        """\
    ...# Editable Git install with no remote (version-pkg==0.1)
    -e {}
    ...""".format(
            os.path.normcase(pkg_path)
        )
    )
    _check_output(result.stdout, expected)


@need_svn
def test_freeze_svn(script, tmpdir):
    """Test freezing a svn checkout"""

    checkout_path = _create_test_package(script, vcs="svn")

    # Install with develop
    script.run("python", "setup.py", "develop", cwd=checkout_path, expect_stderr=True)
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """\
        ...-e svn+...#egg=version_pkg
        ..."""
    )
    _check_output(result.stdout, expected)


@pytest.mark.git
@pytest.mark.xfail(
    condition=True,
    reason="xfail means editable is not in output",
    run=True,
    strict=True,
)
def test_freeze_exclude_editable(script, tmpdir):
    """
    Test excluding editable from freezing list.
    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package(script)

    result = script.run(
        "git",
        "clone",
        pkg_version,
        "pip-test-package",
        expect_stderr=True,
    )
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=repo_dir,
        expect_stderr=True,
    )
    result = script.pip("freeze", "--exclude-editable", expect_stderr=True)
    expected = textwrap.dedent(
        """
            ...-e git+...#egg=version_pkg
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)


@pytest.mark.git
def test_freeze_git_clone(script, tmpdir):
    """
    Test freezing a Git clone.
    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package(script)

    result = script.run(
        "git",
        "clone",
        pkg_version,
        "pip-test-package",
        expect_stderr=True,
    )
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=repo_dir,
        expect_stderr=True,
    )
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """
            ...-e git+...#egg=version_pkg
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)

    # Check that slashes in branch or tag names are translated.
    # See also issue #1083: https://github.com/pypa/pip/issues/1083
    script.run(
        "git",
        "checkout",
        "-b",
        "branch/name/with/slash",
        cwd=repo_dir,
        expect_stderr=True,
    )
    # Create a new commit to ensure that the commit has only one branch
    # or tag name associated to it (to avoid the non-determinism reported
    # in issue #1867).
    (repo_dir / "newfile").touch()
    script.run("git", "add", "newfile", cwd=repo_dir)
    _git_commit(script, repo_dir, message="...")
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """
            ...-e ...@...#egg=version_pkg
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)


@pytest.mark.git
def test_freeze_git_clone_srcdir(script, tmpdir):
    """
    Test freezing a Git clone where setup.py is in a subdirectory
    relative the repo root and the source code is in a subdirectory
    relative to setup.py.
    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package_with_srcdir(script)

    result = script.run(
        "git",
        "clone",
        pkg_version,
        "pip-test-package",
        expect_stderr=True,
    )
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=repo_dir / "subdir",
        expect_stderr=True,
    )
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """
            ...-e git+...#egg=version_pkg&subdirectory=subdir
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)


@need_mercurial
def test_freeze_mercurial_clone_srcdir(script, tmpdir):
    """
    Test freezing a Mercurial clone where setup.py is in a subdirectory
    relative to the repo root and the source code is in a subdirectory
    relative to setup.py.
    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package_with_srcdir(script, vcs="hg")

    result = script.run("hg", "clone", pkg_version, "pip-test-package")
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run("python", "setup.py", "develop", cwd=repo_dir / "subdir")
    result = script.pip("freeze")
    expected = textwrap.dedent(
        """
            ...-e hg+...#egg=version_pkg&subdirectory=subdir
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)


@pytest.mark.git
def test_freeze_git_remote(script, tmpdir):
    """
    Test freezing a Git clone.
    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package(script)

    result = script.run(
        "git",
        "clone",
        pkg_version,
        "pip-test-package",
        expect_stderr=True,
    )
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=repo_dir,
        expect_stderr=True,
    )
    origin_remote = pkg_version
    # check frozen remote after clone
    result = script.pip("freeze", expect_stderr=True)
    expected = (
        textwrap.dedent(
            """
            ...-e git+{remote}@...#egg=version_pkg
            ...
        """
        )
        .format(remote=path_to_url(origin_remote))
        .strip()
    )
    _check_output(result.stdout, expected)
    # check frozen remote when there is no remote named origin
    script.run("git", "remote", "rename", "origin", "other", cwd=repo_dir)
    result = script.pip("freeze", expect_stderr=True)
    expected = (
        textwrap.dedent(
            """
            ...-e git+{remote}@...#egg=version_pkg
            ...
        """
        )
        .format(remote=path_to_url(origin_remote))
        .strip()
    )
    _check_output(result.stdout, expected)
    # When the remote is a local path, it must exist.
    # If it doesn't, it gets flagged as invalid.
    other_remote = pkg_version + "-other"
    script.run("git", "remote", "set-url", "other", other_remote, cwd=repo_dir)
    result = script.pip("freeze", expect_stderr=True)
    expected = os.path.normcase(
        textwrap.dedent(
            f"""
            ...# Editable Git...(version-pkg...)...
            # '{other_remote}'
            -e {repo_dir}...
        """
        ).strip()
    )
    _check_output(os.path.normcase(result.stdout), expected)
    # when there are more than one origin, priority is given to the
    # remote named origin
    script.run("git", "remote", "add", "origin", origin_remote, cwd=repo_dir)
    result = script.pip("freeze", expect_stderr=True)
    expected = (
        textwrap.dedent(
            """
            ...-e git+{remote}@...#egg=version_pkg
            ...
        """
        )
        .format(remote=path_to_url(origin_remote))
        .strip()
    )
    _check_output(result.stdout, expected)


@need_mercurial
def test_freeze_mercurial_clone(script, tmpdir):
    """
    Test freezing a Mercurial clone.

    """
    # Returns path to a generated package called "version_pkg"
    pkg_version = _create_test_package(script, vcs="hg")

    result = script.run(
        "hg",
        "clone",
        pkg_version,
        "pip-test-package",
        expect_stderr=True,
    )
    repo_dir = script.scratch_path / "pip-test-package"
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=repo_dir,
        expect_stderr=True,
    )
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """
            ...-e hg+...#egg=version_pkg
            ...
        """
    ).strip()
    _check_output(result.stdout, expected)


@need_bzr
def test_freeze_bazaar_clone(script, tmpdir):
    """
    Test freezing a Bazaar clone.

    """
    try:
        checkout_path = _create_test_package(script, vcs="bazaar")
    except OSError as e:
        pytest.fail(f"Invoking `bzr` failed: {e}")

    result = script.run("bzr", "checkout", checkout_path, "bzr-package")
    result = script.run(
        "python",
        "setup.py",
        "develop",
        cwd=script.scratch_path / "bzr-package",
        expect_stderr=True,
    )
    result = script.pip("freeze", expect_stderr=True)
    expected = textwrap.dedent(
        """\
        ...-e bzr+file://...@1#egg=version_pkg
        ..."""
    )
    _check_output(result.stdout, expected)


@need_mercurial
@pytest.mark.git
@pytest.mark.parametrize(
    "outer_vcs, inner_vcs",
    [("hg", "git"), ("git", "hg")],
)
def test_freeze_nested_vcs(script, outer_vcs, inner_vcs):
    """Test VCS can be correctly freezed when resides inside another VCS repo."""
    # Create Python package.
    pkg_path = _create_test_package(script, vcs=inner_vcs)

    # Create outer repo to clone into.
    root_path = script.scratch_path.joinpath("test_freeze_nested_vcs")
    root_path.mkdir()
    root_path.joinpath(".hgignore").write_text("src")
    root_path.joinpath(".gitignore").write_text("src")
    _vcs_add(script, root_path, outer_vcs)

    # Clone Python package into inner directory and install it.
    src_path = root_path.joinpath("src")
    src_path.mkdir()
    script.run(inner_vcs, "clone", pkg_path, src_path, expect_stderr=True)
    script.pip("install", "-e", src_path, expect_stderr=True)

    # Check the freeze output recognizes the inner VCS.
    result = script.pip("freeze", expect_stderr=True)
    _check_output(
        result.stdout,
        f"...-e {inner_vcs}+...#egg=version_pkg\n...",
    )


# used by the test_freeze_with_requirement_* tests below
_freeze_req_opts = textwrap.dedent(
    """\
    # Unchanged requirements below this line
    -r ignore.txt
    --requirement ignore.txt
    -f http://ignore
    -i http://ignore
    --pre
    --trusted-host url
    --process-dependency-links
    --extra-index-url http://ignore
    --find-links http://ignore
    --index-url http://ignore
    --use-feature 2020-resolver
"""
)


def test_freeze_with_requirement_option_file_url_egg_not_installed(
    script, deprecated_python
):
    """
    Test "freeze -r requirements.txt" with a local file URL whose egg name
    is not installed.
    """

    url = path_to_url("my-package.tar.gz") + "#egg=Does.Not-Exist"
    requirements_path = script.scratch_path.joinpath("requirements.txt")
    requirements_path.write_text(url + "\n")

    result = script.pip(
        "freeze",
        "--requirement",
        "requirements.txt",
        expect_stderr=True,
    )
    expected_err = (
        "WARNING: Requirement file [requirements.txt] contains {}, "
        "but package 'Does.Not-Exist' is not installed\n"
    ).format(url)
    if deprecated_python:
        assert expected_err in result.stderr
    else:
        assert expected_err == result.stderr


def test_freeze_with_requirement_option(script):
    """
    Test that new requirements are created correctly with --requirement hints

    """

    script.scratch_path.joinpath("hint1.txt").write_text(
        textwrap.dedent(
            """\
        INITools==0.1
        NoExist==4.2  # A comment that ensures end of line comments work.
        simple==3.0; python_version > '1.0'
        """
        )
        + _freeze_req_opts
    )
    script.scratch_path.joinpath("hint2.txt").write_text(
        textwrap.dedent(
            """\
        iniTools==0.1
        Noexist==4.2  # A comment that ensures end of line comments work.
        Simple==3.0; python_version > '1.0'
        """
        )
        + _freeze_req_opts
    )
    result = script.pip_install_local("initools==0.2")
    result = script.pip_install_local("simple")
    result = script.pip(
        "freeze",
        "--requirement",
        "hint1.txt",
        expect_stderr=True,
    )
    expected = textwrap.dedent(
        """\
        INITools==0.2
        simple==3.0
    """
    )
    expected += _freeze_req_opts
    expected += "## The following requirements were added by pip freeze:..."
    _check_output(result.stdout, expected)
    assert (
        "Requirement file [hint1.txt] contains NoExist==4.2, but package "
        "'NoExist' is not installed"
    ) in result.stderr
    result = script.pip(
        "freeze",
        "--requirement",
        "hint2.txt",
        expect_stderr=True,
    )
    _check_output(result.stdout, expected)
    assert (
        "Requirement file [hint2.txt] contains Noexist==4.2, but package "
        "'Noexist' is not installed"
    ) in result.stderr


def test_freeze_with_requirement_option_multiple(script):
    """
    Test that new requirements are created correctly with multiple
    --requirement hints

    """
    script.scratch_path.joinpath("hint1.txt").write_text(
        textwrap.dedent(
            """\
        INITools==0.1
        NoExist==4.2
        simple==3.0; python_version > '1.0'
    """
        )
        + _freeze_req_opts
    )
    script.scratch_path.joinpath("hint2.txt").write_text(
        textwrap.dedent(
            """\
        NoExist2==2.0
        simple2==1.0
    """
        )
        + _freeze_req_opts
    )
    result = script.pip_install_local("initools==0.2")
    result = script.pip_install_local("simple")
    result = script.pip_install_local("simple2==1.0")
    result = script.pip_install_local("meta")
    result = script.pip(
        "freeze",
        "--requirement",
        "hint1.txt",
        "--requirement",
        "hint2.txt",
        expect_stderr=True,
    )
    expected = textwrap.dedent(
        """\
        INITools==0.2
        simple==1.0
    """
    )
    expected += _freeze_req_opts
    expected += textwrap.dedent(
        """\
        simple2==1.0
    """
    )
    expected += "## The following requirements were added by pip freeze:"
    expected += "\n" + textwrap.dedent(
        """\
        ...meta==1.0...
    """
    )
    _check_output(result.stdout, expected)
    assert (
        "Requirement file [hint1.txt] contains NoExist==4.2, but package "
        "'NoExist' is not installed"
    ) in result.stderr
    assert (
        "Requirement file [hint2.txt] contains NoExist2==2.0, but package "
        "'NoExist2' is not installed"
    ) in result.stderr
    # any options like '--index-url http://ignore' should only be emitted once
    # even if they are listed in multiple requirements files
    assert result.stdout.count("--index-url http://ignore") == 1


def test_freeze_with_requirement_option_package_repeated_one_file(script):
    """
    Test freezing with single requirements file that contains a package
    multiple times
    """
    script.scratch_path.joinpath("hint1.txt").write_text(
        textwrap.dedent(
            """\
        simple2
        simple2
        NoExist
    """
        )
        + _freeze_req_opts
    )
    result = script.pip_install_local("simple2==1.0")
    result = script.pip_install_local("meta")
    result = script.pip(
        "freeze",
        "--requirement",
        "hint1.txt",
        expect_stderr=True,
    )
    expected_out = textwrap.dedent(
        """\
        simple2==1.0
    """
    )
    expected_out += _freeze_req_opts
    expected_out += "## The following requirements were added by pip freeze:"
    expected_out += "\n" + textwrap.dedent(
        """\
        ...meta==1.0...
    """
    )
    _check_output(result.stdout, expected_out)
    err1 = (
        "Requirement file [hint1.txt] contains NoExist, "
        "but package 'NoExist' is not installed\n"
    )
    err2 = "Requirement simple2 included multiple times [hint1.txt]\n"
    assert err1 in result.stderr
    assert err2 in result.stderr
    # there shouldn't be any other 'is not installed' warnings
    assert result.stderr.count("is not installed") == 1


def test_freeze_with_requirement_option_package_repeated_multi_file(script):
    """
    Test freezing with multiple requirements file that contain a package
    """
    script.scratch_path.joinpath("hint1.txt").write_text(
        textwrap.dedent(
            """\
        simple
    """
        )
        + _freeze_req_opts
    )
    script.scratch_path.joinpath("hint2.txt").write_text(
        textwrap.dedent(
            """\
        simple
        NoExist
    """
        )
        + _freeze_req_opts
    )
    result = script.pip_install_local("simple==1.0")
    result = script.pip_install_local("meta")
    result = script.pip(
        "freeze",
        "--requirement",
        "hint1.txt",
        "--requirement",
        "hint2.txt",
        expect_stderr=True,
    )
    expected_out = textwrap.dedent(
        """\
        simple==1.0
    """
    )
    expected_out += _freeze_req_opts
    expected_out += "## The following requirements were added by pip freeze:"
    expected_out += "\n" + textwrap.dedent(
        """\
        ...meta==1.0...
    """
    )
    _check_output(result.stdout, expected_out)

    err1 = (
        "Requirement file [hint2.txt] contains NoExist, but package "
        "'NoExist' is not installed\n"
    )
    err2 = "Requirement simple included multiple times [hint1.txt, hint2.txt]\n"
    assert err1 in result.stderr
    assert err2 in result.stderr
    # there shouldn't be any other 'is not installed' warnings
    assert result.stderr.count("is not installed") == 1


@pytest.mark.network
@pytest.mark.incompatible_with_test_venv
def test_freeze_user(script, virtualenv, data):
    """
    Testing freeze with --user, first we have to install some stuff.
    """
    script.pip("download", "setuptools", "wheel", "-d", data.packages)
    script.pip_install_local("--find-links", data.find_links, "--user", "simple==2.0")
    script.pip_install_local("--find-links", data.find_links, "simple2==3.0")
    result = script.pip("freeze", "--user", expect_stderr=True)
    expected = textwrap.dedent(
        """\
        simple==2.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)
    assert "simple2" not in result.stdout


@pytest.mark.network
def test_freeze_path(tmpdir, script, data):
    """
    Test freeze with --path.
    """
    script.pip(
        "install", "--find-links", data.find_links, "--target", tmpdir, "simple==2.0"
    )
    result = script.pip("freeze", "--path", tmpdir)
    expected = textwrap.dedent(
        """\
        simple==2.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)


@pytest.mark.network
@pytest.mark.incompatible_with_test_venv
def test_freeze_path_exclude_user(tmpdir, script, data):
    """
    Test freeze with --path and make sure packages from --user are not picked
    up.
    """
    script.pip_install_local("--find-links", data.find_links, "--user", "simple2")
    script.pip(
        "install", "--find-links", data.find_links, "--target", tmpdir, "simple==1.0"
    )
    result = script.pip("freeze", "--user")
    expected = textwrap.dedent(
        """\
        simple2==3.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)
    result = script.pip("freeze", "--path", tmpdir)
    expected = textwrap.dedent(
        """\
        simple==1.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)


@pytest.mark.network
def test_freeze_path_multiple(tmpdir, script, data):
    """
    Test freeze with multiple --path arguments.
    """
    path1 = tmpdir / "path1"
    os.mkdir(path1)
    path2 = tmpdir / "path2"
    os.mkdir(path2)
    script.pip(
        "install", "--find-links", data.find_links, "--target", path1, "simple==2.0"
    )
    script.pip(
        "install", "--find-links", data.find_links, "--target", path2, "simple2==3.0"
    )
    result = script.pip("freeze", "--path", path1)
    expected = textwrap.dedent(
        """\
        simple==2.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)
    result = script.pip("freeze", "--path", path1, "--path", path2)
    expected = textwrap.dedent(
        """\
        simple==2.0
        simple2==3.0
        <BLANKLINE>"""
    )
    _check_output(result.stdout, expected)


def test_freeze_direct_url_archive(script, shared_data, with_wheel):
    req = "simple @ " + path_to_url(shared_data.packages / "simple-2.0.tar.gz")
    assert req.startswith("simple @ file://")
    script.pip("install", req)
    result = script.pip("freeze")
    assert req in result.stdout


def test_freeze_skip_work_dir_pkg(script):
    """
    Test that freeze should not include package
    present in working directory
    """

    # Create a test package and create .egg-info dir
    pkg_path = create_test_package_with_setup(script, name="simple", version="1.0")
    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    # Freeze should not include package simple when run from package directory
    result = script.pip("freeze", cwd=pkg_path)
    assert "simple" not in result.stdout


def test_freeze_include_work_dir_pkg(script):
    """
    Test that freeze should include package in working directory
    if working directory is added in PYTHONPATH
    """

    # Create a test package and create .egg-info dir
    pkg_path = create_test_package_with_setup(script, name="simple", version="1.0")
    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    script.environ.update({"PYTHONPATH": pkg_path})

    # Freeze should include package simple when run from package directory,
    # when package directory is in PYTHONPATH
    result = script.pip("freeze", cwd=pkg_path)
    assert "simple==1.0" in result.stdout
