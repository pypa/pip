import hashlib
import os
import re
import ssl
import sys
import sysconfig
import textwrap
from os.path import curdir, join, pardir
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.models.index import PyPI, TestPyPI
from pip._internal.utils.misc import rmtree
from pip._internal.utils.urls import path_to_url
from tests.conftest import CertFactory
from tests.lib import (
    PipTestEnvironment,
    ResolverVariant,
    TestData,
    TestPipResult,
    _create_svn_repo,
    _create_test_package,
    create_basic_wheel_for_package,
    create_test_package_with_setup,
    need_bzr,
    need_mercurial,
    need_svn,
    pyversion,
    requirements_file,
)
from tests.lib.local_repos import local_checkout
from tests.lib.server import (
    file_response,
    make_mock_server,
    package_page,
    server_running,
)


@pytest.mark.parametrize("command", ("install", "wheel"))
@pytest.mark.parametrize("variant", ("missing_setuptools", "bad_setuptools"))
def test_pep518_uses_build_env(
    script: PipTestEnvironment,
    data: TestData,
    common_wheels: Path,
    command: str,
    variant: str,
) -> None:
    if variant == "missing_setuptools":
        script.pip("uninstall", "-y", "setuptools")
    elif variant == "bad_setuptools":
        setuptools_mod = script.site_packages_path.joinpath("setuptools.py")
        with open(setuptools_mod, "a") as f:
            f.write('\nraise ImportError("toto")')
    else:
        raise ValueError(variant)
    script.pip(
        command,
        "--no-index",
        "-f",
        common_wheels,
        "-f",
        data.packages,
        data.src.joinpath("pep518-3.0"),
    )


def test_pep518_build_env_uses_same_pip(
    script: PipTestEnvironment,
    data: TestData,
    pip_src: Path,
    common_wheels: Path,
    deprecated_python: bool,
) -> None:
    """Ensure the subprocess call to pip for installing the
    build dependencies is using the same version of pip.
    """
    with open(script.scratch_path / "pip.py", "w") as fp:
        fp.write("raise ImportError")
    script.run(
        "python",
        os.fspath(pip_src / "src/pip"),
        "install",
        "--no-index",
        "-f",
        os.fspath(common_wheels),
        "-f",
        os.fspath(data.packages),
        os.fspath(data.src.joinpath("pep518-3.0")),
        expect_stderr=deprecated_python,
    )


def test_pep518_refuses_conflicting_requires(
    script: PipTestEnvironment, data: TestData
) -> None:
    create_basic_wheel_for_package(script, "setuptools", "1.0")
    create_basic_wheel_for_package(script, "wheel", "1.0")
    project_dir = data.src.joinpath("pep518_conflicting_requires")
    result = script.pip_install_local(
        "-f", script.scratch_path, project_dir, expect_error=True
    )
    assert (
        result.returncode != 0
        and (
            "Some build dependencies for {url} conflict "
            "with PEP 517/518 supported "
            "requirements: setuptools==1.0 is incompatible with "
            "setuptools>=40.8.0.".format(url=project_dir.as_uri())
        )
        in result.stderr
    ), str(result)


def test_pep518_refuses_invalid_requires(
    script: PipTestEnvironment, data: TestData, common_wheels: Path
) -> None:
    result = script.pip(
        "install",
        "-f",
        common_wheels,
        data.src.joinpath("pep518_invalid_requires"),
        expect_error=True,
    )
    assert result.returncode == 1

    # Ensure the relevant things are mentioned.
    assert "PEP 518" in result.stderr
    assert "not a list of strings" in result.stderr
    assert "build-system.requires" in result.stderr
    assert "pyproject.toml" in result.stderr


def test_pep518_refuses_invalid_build_system(
    script: PipTestEnvironment, data: TestData, common_wheels: Path
) -> None:
    result = script.pip(
        "install",
        "-f",
        common_wheels,
        data.src.joinpath("pep518_invalid_build_system"),
        expect_error=True,
    )
    assert result.returncode == 1

    # Ensure the relevant things are mentioned.
    assert "PEP 518" in result.stderr
    assert "mandatory `requires` key" in result.stderr
    assert "[build-system] table" in result.stderr
    assert "pyproject.toml" in result.stderr


def test_pep518_allows_missing_requires(
    script: PipTestEnvironment, data: TestData, common_wheels: Path
) -> None:
    result = script.pip(
        "install",
        "-f",
        common_wheels,
        data.src.joinpath("pep518_missing_requires"),
        expect_stderr=True,
    )
    # Make sure we don't warn when this occurs.
    assert "PEP 518" not in result.stderr

    # We want it to go through isolation for now.
    assert "Installing build dependencies" in result.stdout, result.stdout

    assert result.returncode == 0
    assert result.files_created


@pytest.mark.usefixtures("enable_user_site")
def test_pep518_with_user_pip(
    script: PipTestEnvironment, pip_src: Path, data: TestData, common_wheels: Path
) -> None:
    """
    Check that build dependencies are installed into the build
    environment without using build isolation for the pip invocation.

    To ensure that we're not using build isolation when installing
    the build dependencies, we install a user copy of pip in the
    non-isolated environment, and break pip in the system site-packages,
    so that isolated uses of pip will fail.
    """
    script.pip(
        "install",
        "--ignore-installed",
        "-f",
        common_wheels,
        "--user",
        pip_src,
        # WARNING: The scripts pip, pip3, ... are installed in ... which is not on PATH
        allow_stderr_warning=True,
    )
    system_pip_dir = script.site_packages_path / "pip"
    assert not system_pip_dir.exists()
    system_pip_dir.mkdir()
    with open(system_pip_dir / "__init__.py", "w") as fp:
        fp.write("raise ImportError\n")
    script.pip(
        "wheel",
        "--no-index",
        "-f",
        common_wheels,
        "-f",
        data.packages,
        data.src.joinpath("pep518-3.0"),
    )


def test_pep518_with_extra_and_markers(
    script: PipTestEnvironment, data: TestData, common_wheels: Path
) -> None:
    script.pip(
        "wheel",
        "--no-index",
        "-f",
        common_wheels,
        "-f",
        data.find_links,
        data.src.joinpath("pep518_with_extra_and_markers-1.0"),
    )


def test_pep518_with_namespace_package(
    script: PipTestEnvironment, data: TestData, common_wheels: Path
) -> None:
    script.pip(
        "wheel",
        "--no-index",
        "-f",
        common_wheels,
        "-f",
        data.find_links,
        data.src.joinpath("pep518_with_namespace_package-1.0"),
        use_module=True,
    )


@pytest.mark.parametrize("command", ("install", "wheel"))
@pytest.mark.parametrize(
    "package",
    ("pep518_forkbomb", "pep518_twin_forkbombs_first", "pep518_twin_forkbombs_second"),
)
def test_pep518_forkbombs(
    script: PipTestEnvironment,
    data: TestData,
    common_wheels: Path,
    command: str,
    package: str,
) -> None:
    package_source = next(data.packages.glob(package + "-[0-9]*.tar.gz"))
    result = script.pip(
        command,
        "--no-index",
        "-v",
        "-f",
        common_wheels,
        "-f",
        data.find_links,
        package,
        expect_error=True,
    )
    assert (
        "{1} is already being built: {0} from {1}".format(
            package,
            package_source.as_uri(),
        )
        in result.stderr
    ), str(result)


@pytest.mark.network
def test_pip_second_command_line_interface_works(
    script: PipTestEnvironment,
    pip_src: Path,
    data: TestData,
    common_wheels: Path,
    deprecated_python: bool,
) -> None:
    """
    Check if ``pip<PYVERSION>`` commands behaves equally
    """
    # Re-install pip so we get the launchers.
    script.pip_install_local("-f", common_wheels, pip_src)
    args = [f"pip{pyversion}"]
    args.extend(["install", "INITools==0.2"])
    args.extend(["-f", os.fspath(data.packages)])
    result = script.run(*args)
    dist_info_folder = script.site_packages / "INITools-0.2.dist-info"
    initools_folder = script.site_packages / "initools"
    result.did_create(dist_info_folder)
    result.did_create(initools_folder)


def test_install_exit_status_code_when_no_requirements(
    script: PipTestEnvironment,
) -> None:
    """
    Test install exit status code when no requirements specified
    """
    result = script.pip("install", expect_error=True)
    assert "You must give at least one requirement to install" in result.stderr
    assert result.returncode == ERROR


def test_install_exit_status_code_when_blank_requirements_file(
    script: PipTestEnvironment,
) -> None:
    """
    Test install exit status code when blank requirements file specified
    """
    script.scratch_path.joinpath("blank.txt").write_text("\n")
    script.pip("install", "-r", "blank.txt")


@pytest.mark.network
def test_basic_install_from_pypi(script: PipTestEnvironment) -> None:
    """
    Test installing a package from PyPI.
    """
    result = script.pip("install", "INITools==0.2")
    dist_info_folder = script.site_packages / "INITools-0.2.dist-info"
    initools_folder = script.site_packages / "initools"
    result.did_create(dist_info_folder)
    result.did_create(initools_folder)

    # Should not display where it's looking for files
    assert "Looking in indexes: " not in result.stdout
    assert "Looking in links: " not in result.stdout

    # Ensure that we don't print the full URL.
    #    The URL should be trimmed to only the last part of the path in it,
    #    when installing from PyPI. The assertion here only checks for
    #    `https://` since that's likely to show up if we're not trimming in
    #    the correct circumstances.
    assert "https://" not in result.stdout


def test_basic_editable_install(script: PipTestEnvironment) -> None:
    """
    Test editable installation.
    """
    result = script.pip("install", "-e", "INITools==0.2", expect_error=True)
    assert "INITools==0.2 is not a valid editable requirement" in result.stderr
    assert not result.files_created


@need_svn
def test_basic_install_editable_from_svn(script: PipTestEnvironment) -> None:
    """
    Test checking out from svn.
    """
    checkout_path = _create_test_package(script.scratch_path)
    repo_url = _create_svn_repo(script.scratch_path, checkout_path)
    result = script.pip("install", "-e", "svn+" + repo_url + "#egg=version-pkg")
    result.assert_installed("version-pkg", with_files=[".svn"])


def _test_install_editable_from_git(script: PipTestEnvironment) -> None:
    """Test cloning from Git."""
    pkg_path = _create_test_package(script.scratch_path, name="testpackage", vcs="git")
    args = [
        "install",
        "-e",
        f"git+{pkg_path.as_uri()}#egg=testpackage",
    ]
    result = script.pip(*args)
    result.assert_installed("testpackage", with_files=[".git"])


def test_basic_install_editable_from_git(script: PipTestEnvironment) -> None:
    _test_install_editable_from_git(script)


def test_install_editable_from_git_autobuild_wheel(script: PipTestEnvironment) -> None:
    _test_install_editable_from_git(script)


@pytest.mark.network
def test_install_editable_uninstalls_existing(
    data: TestData, script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test that installing an editable uninstalls a previously installed
    non-editable version.
    https://github.com/pypa/pip/issues/1548
    https://github.com/pypa/pip/pull/1552
    """
    to_install = data.packages.joinpath("pip-test-package-0.1.tar.gz")
    result = script.pip_install_local(to_install)
    assert "Successfully installed pip-test-package" in result.stdout
    result.assert_installed("piptestpackage", editable=False)

    result = script.pip(
        "install",
        "-e",
        "{dir}#egg=pip-test-package".format(
            dir=local_checkout(
                "git+https://github.com/pypa/pip-test-package.git",
                tmpdir,
            )
        ),
    )
    result.assert_installed("pip-test-package", with_files=[".git"])
    assert "Found existing installation: pip-test-package 0.1" in result.stdout
    assert "Uninstalling pip-test-package-" in result.stdout
    assert "Successfully uninstalled pip-test-package" in result.stdout


def test_install_editable_uninstalls_existing_from_path(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that installing an editable uninstalls a previously installed
    non-editable version from path
    """
    to_install = data.src.joinpath("simplewheel-1.0")
    result = script.pip_install_local(to_install)
    assert "Successfully installed simplewheel" in result.stdout
    simple_folder = script.site_packages / "simplewheel"
    result.assert_installed("simplewheel", editable=False)
    result.did_create(simple_folder)

    result = script.pip(
        "install",
        "-e",
        to_install,
    )
    install_path = script.site_packages / "simplewheel.egg-link"
    result.did_create(install_path)
    assert "Found existing installation: simplewheel 1.0" in result.stdout
    assert "Uninstalling simplewheel-" in result.stdout
    assert "Successfully uninstalled simplewheel" in result.stdout
    assert simple_folder in result.files_deleted, str(result.stdout)


@need_mercurial
def test_basic_install_editable_from_hg(script: PipTestEnvironment) -> None:
    """Test cloning and hg+file install from Mercurial."""
    pkg_path = _create_test_package(script.scratch_path, name="testpackage", vcs="hg")
    url = f"hg+{pkg_path.as_uri()}#egg=testpackage"
    assert url.startswith("hg+file")
    args = ["install", "-e", url]
    result = script.pip(*args)
    result.assert_installed("testpackage", with_files=[".hg"])


@need_mercurial
def test_vcs_url_final_slash_normalization(script: PipTestEnvironment) -> None:
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    """
    pkg_path = _create_test_package(script.scratch_path, name="testpackage", vcs="hg")
    args = [
        "install",
        "-e",
        f"hg+{pkg_path.as_uri()}/#egg=testpackage",
    ]
    result = script.pip(*args)
    result.assert_installed("testpackage", with_files=[".hg"])


@need_bzr
def test_install_editable_from_bazaar(script: PipTestEnvironment) -> None:
    """Test checking out from Bazaar."""
    pkg_path = _create_test_package(
        script.scratch_path, name="testpackage", vcs="bazaar"
    )
    args = [
        "install",
        "-e",
        f"bzr+{pkg_path.as_uri()}/#egg=testpackage",
    ]
    result = script.pip(*args)
    result.assert_installed("testpackage", with_files=[".bzr"])


@pytest.mark.network
@need_bzr
def test_vcs_url_urlquote_normalization(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test that urlquoted characters are normalized for repo URL comparison.
    """
    script.pip(
        "install",
        "-e",
        "{url}/#egg=django-wikiapp".format(
            url=local_checkout(
                "bzr+http://bazaar.launchpad.net/"
                "%7Edjango-wikiapp/django-wikiapp"
                "/release-0.1",
                tmpdir,
            )
        ),
    )


@pytest.mark.parametrize("resolver", ["", "--use-deprecated=legacy-resolver"])
def test_basic_install_from_local_directory(
    script: PipTestEnvironment, data: TestData, resolver: str
) -> None:
    """
    Test installing from a local directory.
    """
    args = ["install"]
    if resolver:
        args.append(resolver)
    to_install = data.packages.joinpath("FSPkg")
    args.append(os.fspath(to_install))
    result = script.pip(*args)
    fspkg_folder = script.site_packages / "fspkg"
    dist_info_folder = script.site_packages / "FSPkg-0.1.dev0.dist-info"
    result.did_create(fspkg_folder)
    result.did_create(dist_info_folder)


@pytest.mark.parametrize(
    "test_type,editable",
    [
        ("rel_path", False),
        ("rel_path", True),
        ("rel_url", False),
        ("rel_url", True),
        ("embedded_rel_path", False),
        ("embedded_rel_path", True),
    ],
)
def test_basic_install_relative_directory(
    script: PipTestEnvironment, data: TestData, test_type: str, editable: bool
) -> None:
    """
    Test installing a requirement using a relative path.
    """
    dist_info_folder = script.site_packages / "FSPkg-0.1.dev0.dist-info"
    egg_link_file = script.site_packages / "FSPkg.egg-link"
    package_folder = script.site_packages / "fspkg"

    # Compute relative install path to FSPkg from scratch path.
    full_rel_path = Path(
        os.path.relpath(data.packages.joinpath("FSPkg"), script.scratch_path)
    )
    full_rel_url = f"file:{full_rel_path.as_posix()}#egg=FSPkg"
    embedded_rel_path = script.scratch_path.joinpath(full_rel_path)

    req_path = {
        "rel_path": os.fspath(full_rel_path),
        "rel_url": full_rel_url,
        "embedded_rel_path": os.fspath(embedded_rel_path),
    }[test_type]

    # Install as either editable or not.
    if not editable:
        result = script.pip("install", req_path, cwd=script.scratch_path)
        result.did_create(dist_info_folder)
        result.did_create(package_folder)
    else:
        # Editable install.
        result = script.pip("install", "-e", req_path, cwd=script.scratch_path)
        result.did_create(egg_link_file)


def test_install_quiet(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that install -q is actually quiet.
    """
    # Apparently if pip install -q is not actually quiet, then it breaks
    # everything. See:
    #   https://github.com/pypa/pip/issues/3418
    #   https://github.com/docker-library/python/issues/83
    to_install = data.packages.joinpath("FSPkg")
    result = script.pip("install", "-qqq", to_install)
    assert result.stdout == ""
    assert result.stderr == ""


def test_hashed_install_success(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """
    Test that installing various sorts of requirements with correct hashes
    works.

    Test file URLs and index packages (which become HTTP URLs behind the
    scenes).

    """
    file_url = data.packages.joinpath("simple-1.0.tar.gz").resolve().as_uri()
    with requirements_file(
        "simple2==1.0 --hash=sha256:9336af72ca661e6336eb87bc7de3e8844d853e"
        "3848c2b9bbd2e8bf01db88c2c7\n"
        "{simple} --hash=sha256:393043e672415891885c9a2a0929b1af95fb866d6c"
        "a016b42d2e6ce53619b653".format(simple=file_url),
        tmpdir,
    ) as reqs_file:
        script.pip_install_local("-r", reqs_file.resolve())


def test_hashed_install_failure(script: PipTestEnvironment, tmpdir: Path) -> None:
    """Test that wrong hashes stop installation.

    This makes sure prepare_files() is called in the course of installation
    and so has the opportunity to halt if hashes are wrong. Checks on various
    kinds of hashes are in test_req.py.

    """
    with requirements_file(
        "simple2==1.0 --hash=sha256:9336af72ca661e6336eb87b"
        "c7de3e8844d853e3848c2b9bbd2e8bf01db88c2c\n",
        tmpdir,
    ) as reqs_file:
        result = script.pip_install_local("-r", reqs_file.resolve(), expect_error=True)
    assert len(result.files_created) == 0


def test_link_hash_pass_require_hashes(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """Test that a good hash in user provided direct URL is
    considered valid for --require-hashes."""
    url = path_to_url(str(shared_data.packages.joinpath("simple-1.0.tar.gz")))
    url = (
        f"{url}#sha256="
        "393043e672415891885c9a2a0929b1af95fb866d6ca016b42d2e6ce53619b653"
    )
    script.pip_install_local("--no-deps", "--require-hashes", url)


def test_bad_link_hash_install_failure(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """Test that wrong hash in direct URL stops installation."""
    url = path_to_url(str(shared_data.packages.joinpath("simple-1.0.tar.gz")))
    url = f"{url}#sha256=invalidhash"
    result = script.pip_install_local("--no-deps", url, expect_error=True)
    assert "THESE PACKAGES DO NOT MATCH THE HASHES" in result.stderr


def test_bad_link_hash_good_user_hash_install_success(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    """Test that wrong hash in direct URL ignored when good --hash provided.

    This behaviour may be accidental?
    """
    url = path_to_url(str(shared_data.packages.joinpath("simple-1.0.tar.gz")))
    url = f"{url}#sha256=invalidhash"
    digest = "393043e672415891885c9a2a0929b1af95fb866d6ca016b42d2e6ce53619b653"
    with requirements_file(
        f"simple @ {url} --hash sha256:{digest}", tmp_path
    ) as reqs_file:
        script.pip_install_local("--no-deps", "--require-hashes", "-r", reqs_file)


def test_link_hash_in_dep_fails_require_hashes(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test that a good hash in direct URL dependency is not considered
    for --require-hashes."""
    # Create a project named pkga that depends on the simple-1.0.tar.gz with a direct
    # URL including a hash.
    simple_url = path_to_url(str(shared_data.packages.joinpath("simple-1.0.tar.gz")))
    simple_url_with_hash = (
        f"{simple_url}#sha256="
        "393043e672415891885c9a2a0929b1af95fb866d6ca016b42d2e6ce53619b653"
    )
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [project]
            name = "pkga"
            version = "1.0"
            dependencies = ["simple @ {simple_url_with_hash}"]
            """
        )
    )
    # Build a wheel for pkga and compute its hash.
    wheelhouse = tmp_path / "wheehouse"
    wheelhouse.mkdir()
    script.pip("wheel", "--no-deps", "-w", wheelhouse, project_path)
    digest = hashlib.sha256(
        wheelhouse.joinpath("pkga-1.0-py3-none-any.whl").read_bytes()
    ).hexdigest()
    # Install pkga from a requirements file with hash, using --require-hashes.
    # This should fail because we have not provided a hash for the 'simple' dependency.
    with requirements_file(f"pkga==1.0 --hash sha256:{digest}", tmp_path) as reqs_file:
        result = script.pip(
            "install",
            "--no-build-isolation",
            "--require-hashes",
            "--no-index",
            "-f",
            wheelhouse,
            "-r",
            reqs_file,
            expect_error=True,
        )
    assert "Hashes are required in --require-hashes mode" in result.stderr


def test_bad_link_hash_in_dep_install_failure(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test that wrong hash in direct URL dependency stops installation."""
    url = path_to_url(str(shared_data.packages.joinpath("simple-1.0.tar.gz")))
    url = f"{url}#sha256=invalidhash"
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [project]
            name = "pkga"
            version = "1.0"
            dependencies = ["simple @ {url}"]
            """
        )
    )
    result = script.pip_install_local(
        "--no-build-isolation", project_path, expect_error=True
    )
    assert "THESE PACKAGES DO NOT MATCH THE HASHES" in result.stderr, result.stderr


def test_hashed_install_from_cache(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """
    Test that installing from a cached built wheel works and that the hash is verified
    against the hash of the original source archived stored in the cache entry.
    """
    with requirements_file(
        "simple2==1.0 --hash=sha256:"
        "9336af72ca661e6336eb87bc7de3e8844d853e3848c2b9bbd2e8bf01db88c2c7\n",
        tmpdir,
    ) as reqs_file:
        result = script.pip_install_local(
            "--use-pep517", "--no-build-isolation", "-r", reqs_file.resolve()
        )
        assert "Created wheel for simple2" in result.stdout
        script.pip("uninstall", "simple2", "-y")
        result = script.pip_install_local(
            "--use-pep517", "--no-build-isolation", "-r", reqs_file.resolve()
        )
        assert "Using cached simple2" in result.stdout
    # now try with an invalid hash
    with requirements_file(
        "simple2==1.0 --hash=sha256:invalid\n",
        tmpdir,
    ) as reqs_file:
        script.pip("uninstall", "simple2", "-y")
        result = script.pip_install_local(
            "--use-pep517",
            "--no-build-isolation",
            "-r",
            reqs_file.resolve(),
            expect_error=True,
        )
        assert (
            "WARNING: The hashes of the source archive found in cache entry "
            "don't match, ignoring cached built wheel and re-downloading source."
        ) in result.stderr
        assert "Using cached simple2" in result.stdout
        assert "ERROR: THESE PACKAGES DO NOT MATCH THE HASHES" in result.stderr


def assert_re_match(pattern: str, text: str) -> None:
    assert re.search(pattern, text), f"Could not find {pattern!r} in {text!r}"


@pytest.mark.network
@pytest.mark.skip("Fails on new resolver")
def test_hashed_install_failure_later_flag(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    with requirements_file(
        "blessings==1.0\n"
        "tracefront==0.1 --hash=sha256:somehash\n"
        "https://files.pythonhosted.org/packages/source/m/more-itertools/"
        "more-itertools-1.0.tar.gz#md5=b21850c3cfa7efbb70fd662ab5413bdd\n"
        "https://files.pythonhosted.org/"
        "packages/source/p/peep/peep-3.1.1.tar.gz\n",
        tmpdir,
    ) as reqs_file:
        result = script.pip("install", "-r", reqs_file.resolve(), expect_error=True)

    assert_re_match(
        r"Hashes are required in --require-hashes mode, but they are "
        r"missing .*\n"
        r"    https://files\.pythonhosted\.org/packages/source/p/peep/peep"
        r"-3\.1\.1\.tar\.gz --hash=sha256:[0-9a-f]+\n"
        r"    blessings==1.0 --hash=sha256:[0-9a-f]+\n"
        r"THESE PACKAGES DO NOT MATCH THE HASHES.*\n"
        r"    tracefront==0.1 .*:\n"
        r"        Expected sha256 somehash\n"
        r"             Got        [0-9a-f]+",
        result.stderr,
    )


def test_install_from_local_directory_with_in_tree_build(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing from a local directory with default in tree build.
    """
    to_install = data.packages.joinpath("FSPkg")

    in_tree_build_dir = to_install / "build"
    assert not in_tree_build_dir.exists()
    result = script.pip("install", to_install)
    fspkg_folder = script.site_packages / "fspkg"
    dist_info_folder = script.site_packages / "FSPkg-0.1.dev0.dist-info"
    result.did_create(fspkg_folder)
    result.did_create(dist_info_folder)
    assert in_tree_build_dir.exists()


def test_install_from_local_directory_with_no_setup_py(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing from a local directory with no 'setup.py'.
    """
    result = script.pip("install", data.root, expect_error=True)
    assert not result.files_created
    assert "Neither 'setup.py' nor 'pyproject.toml' found." in result.stderr


def test_editable_install__local_dir_no_setup_py(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing in editable mode from a local directory with no setup.py.
    """
    result = script.pip("install", "-e", data.root, expect_error=True)
    assert not result.files_created
    assert (
        "does not appear to be a Python project: "
        "neither 'setup.py' nor 'pyproject.toml' found" in result.stderr
    )


@pytest.mark.skipif(
    sys.version_info >= (3, 12),
    reason="Setuptools<64 does not support Python 3.12+",
)
@pytest.mark.network
def test_editable_install_legacy__local_dir_no_setup_py_with_pyproject(
    script: PipTestEnvironment,
) -> None:
    """
    Test installing in legacy editable mode from a local directory with no
    setup.py but that does have pyproject.toml with a build backend that does
    not support the build_editable hook.
    """
    local_dir = script.scratch_path.joinpath("temp")
    local_dir.mkdir()
    pyproject_path = local_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(
        textwrap.dedent(
            """
                [build-system]
                requires = ["setuptools<64"]
                build-backend = "setuptools.build_meta"
            """
        )
    )

    result = script.pip("install", "-e", local_dir, expect_error=True)
    assert not result.files_created

    msg = result.stderr
    assert "has a 'pyproject.toml'" in msg
    assert "does not have a 'setup.py' nor a 'setup.cfg'" in msg
    assert "cannot be installed in editable mode" in msg


def test_editable_install__local_dir_setup_requires_with_pyproject(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """
    Test installing in editable mode from a local directory with a setup.py
    that has setup_requires and a pyproject.toml.

    https://github.com/pypa/pip/issues/10573
    """
    local_dir = script.scratch_path.joinpath("temp")
    local_dir.mkdir()
    pyproject_path = local_dir.joinpath("pyproject.toml")
    pyproject_path.write_text("")
    setup_py_path = local_dir.joinpath("setup.py")
    setup_py_path.write_text(
        "from setuptools import setup\n"
        "setup(name='dummy', setup_requires=['simplewheel'])\n"
    )

    script.pip("install", "--find-links", shared_data.find_links, "-e", local_dir)


def test_install_pre__setup_requires_with_pyproject(
    script: PipTestEnvironment, shared_data: TestData, common_wheels: Path
) -> None:
    """
    Test installing with a pre-release build dependency declared in both
    setup.py and pyproject.toml.

    https://github.com/pypa/pip/issues/10573
    """
    depends_package = "prerelease_dependency"
    depends_path = create_basic_wheel_for_package(script, depends_package, "1.0.0a1")

    local_dir = script.scratch_path.joinpath("temp")
    local_dir.mkdir()
    pyproject_path = local_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(
        "[build-system]\n"
        f'requires = ["setuptools", "wheel", "{depends_package}"]\n'
        'build-backend = "setuptools.build_meta"\n'
    )
    setup_py_path = local_dir.joinpath("setup.py")
    setup_py_path.write_text(
        "from setuptools import setup\n"
        f"setup(name='dummy', setup_requires=['{depends_package}'])\n"
    )

    script.pip(
        "install",
        "--pre",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        common_wheels,
        "--find-links",
        depends_path.parent,
        local_dir,
    )


@pytest.mark.network
def test_upgrade_argparse_shadowed(script: PipTestEnvironment) -> None:
    # If argparse is installed - even if shadowed for imported - we support
    # upgrading it and properly remove the older versions files.
    script.pip("install", "argparse==1.3")
    result = script.pip("install", "argparse>=1.4")
    assert "Not uninstalling argparse" not in result.stdout


def test_install_curdir(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test installing current directory ('.').
    """
    run_from = data.packages.joinpath("FSPkg")
    # Python 2.4 Windows balks if this exists already
    egg_info = join(run_from, "FSPkg.egg-info")
    if os.path.isdir(egg_info):
        rmtree(egg_info)
    result = script.pip("install", curdir, cwd=run_from)
    fspkg_folder = script.site_packages / "fspkg"
    dist_info_folder = script.site_packages / "FSPkg-0.1.dev0.dist-info"
    result.did_create(fspkg_folder)
    result.did_create(dist_info_folder)


def test_install_pardir(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test installing parent directory ('..').
    """
    run_from = data.packages.joinpath("FSPkg", "fspkg")
    result = script.pip("install", pardir, cwd=run_from)
    fspkg_folder = script.site_packages / "fspkg"
    dist_info_folder = script.site_packages / "FSPkg-0.1.dev0.dist-info"
    result.did_create(fspkg_folder)
    result.did_create(dist_info_folder)


@pytest.mark.network
def test_install_global_option(script: PipTestEnvironment) -> None:
    """
    Test using global distutils options.
    (In particular those that disable the actual install action)
    """
    result = script.pip(
        "install",
        "--global-option=--version",
        "INITools==0.1",
        expect_error=True,  # build is going to fail because of --version
    )
    assert "INITools==0.1\n" in result.stdout
    assert not result.files_created
    assert "Implying --no-binary=:all:" in result.stderr
    assert "A possible replacement is to use --config-settings" in result.stderr


def test_install_with_hacked_egg_info(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    test installing a package which defines its own egg_info class
    """
    run_from = data.packages.joinpath("HackedEggInfo")
    result = script.pip("install", ".", cwd=run_from)
    assert "Successfully installed hackedegginfo-0.0.0\n" in result.stdout


@pytest.mark.xfail
@pytest.mark.network
@need_mercurial
def test_install_global_option_using_editable(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """
    Test using global distutils options, but in an editable installation
    """
    url = "hg+http://bitbucket.org/runeh/anyjson"
    result = script.pip(
        "install",
        "--global-option=--version",
        "-e",
        f"{local_checkout(url, tmpdir)}@0.2.5#egg=anyjson",
        expect_stderr=True,
    )
    assert "Successfully installed anyjson" in result.stdout


@pytest.mark.network
def test_install_package_with_same_name_in_curdir(script: PipTestEnvironment) -> None:
    """
    Test installing a package with the same name of a local folder
    """
    script.scratch_path.joinpath("mock==0.6").mkdir()
    result = script.pip("install", "mock==0.6")
    dist_info_folder = script.site_packages / "mock-0.6.0.dist-info"
    result.did_create(dist_info_folder)


mock100_setup_py = textwrap.dedent(
    """\
                        from setuptools import setup
                        setup(name='mock',
                              version='100.1')"""
)


def test_install_folder_using_dot_slash(script: PipTestEnvironment) -> None:
    """
    Test installing a folder using pip install ./foldername
    """
    script.scratch_path.joinpath("mock").mkdir()
    pkg_path = script.scratch_path / "mock"
    pkg_path.joinpath("setup.py").write_text(mock100_setup_py)
    result = script.pip("install", "./mock")
    dist_info_folder = script.site_packages / "mock-100.1.dist-info"
    result.did_create(dist_info_folder)


def test_install_folder_using_slash_in_the_end(script: PipTestEnvironment) -> None:
    r"""
    Test installing a folder using pip install foldername/ or foldername\
    """
    script.scratch_path.joinpath("mock").mkdir()
    pkg_path = script.scratch_path / "mock"
    pkg_path.joinpath("setup.py").write_text(mock100_setup_py)
    result = script.pip("install", "mock" + os.path.sep)
    dist_info_folder = script.site_packages / "mock-100.1.dist-info"
    result.did_create(dist_info_folder)


def test_install_folder_using_relative_path(script: PipTestEnvironment) -> None:
    """
    Test installing a folder using pip install folder1/folder2
    """
    script.scratch_path.joinpath("initools").mkdir()
    script.scratch_path.joinpath("initools", "mock").mkdir()
    pkg_path = script.scratch_path / "initools" / "mock"
    pkg_path.joinpath("setup.py").write_text(mock100_setup_py)
    result = script.pip("install", Path("initools") / "mock")
    dist_info_folder = script.site_packages / "mock-100.1.dist-info"
    result.did_create(dist_info_folder)


@pytest.mark.network
def test_install_package_which_contains_dev_in_name(script: PipTestEnvironment) -> None:
    """
    Test installing package from PyPI which contains 'dev' in name
    """
    result = script.pip("install", "django-devserver==0.0.4")
    devserver_folder = script.site_packages / "devserver"
    dist_info_folder = script.site_packages / "django_devserver-0.0.4.dist-info"
    result.did_create(devserver_folder)
    result.did_create(dist_info_folder)


def test_install_package_with_target(script: PipTestEnvironment) -> None:
    """
    Test installing a package using pip install --target
    """
    target_dir = script.scratch_path / "target"
    result = script.pip_install_local("-t", target_dir, "simple==1.0")
    result.did_create(Path("scratch") / "target" / "simple")

    # Test repeated call without --upgrade, no files should have changed
    result = script.pip_install_local(
        "-t",
        target_dir,
        "simple==1.0",
        expect_stderr=True,
    )
    result.did_not_update(Path("scratch") / "target" / "simple")

    # Test upgrade call, check that new version is installed
    result = script.pip_install_local("--upgrade", "-t", target_dir, "simple==2.0")
    result.did_update(Path("scratch") / "target" / "simple")
    dist_info_folder = Path("scratch") / "target" / "simple-2.0.dist-info"
    result.did_create(dist_info_folder)

    # Test install and upgrade of single-module package
    result = script.pip_install_local("-t", target_dir, "singlemodule==0.0.0")
    singlemodule_py = Path("scratch") / "target" / "singlemodule.py"
    result.did_create(singlemodule_py)

    result = script.pip_install_local(
        "-t", target_dir, "singlemodule==0.0.1", "--upgrade"
    )
    result.did_update(singlemodule_py)


@pytest.mark.parametrize("target_option", ["--target", "-t"])
def test_install_package_to_usersite_with_target_must_fail(
    script: PipTestEnvironment, target_option: str
) -> None:
    """
    Test that installing package to usersite with target
    must raise error
    """
    target_dir = script.scratch_path / "target"
    result = script.pip_install_local(
        "--user", target_option, target_dir, "simple==1.0", expect_error=True
    )
    assert "Can not combine '--user' and '--target'" in result.stderr, str(result)


def test_install_nonlocal_compatible_wheel(
    script: PipTestEnvironment, data: TestData
) -> None:
    target_dir = script.scratch_path / "target"

    # Test install with --target
    result = script.pip(
        "install",
        "-t",
        target_dir,
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--python-version",
        "3",
        "--platform",
        "fakeplat",
        "--abi",
        "fakeabi",
        "simplewheel",
    )
    assert result.returncode == SUCCESS

    distinfo = Path("scratch") / "target" / "simplewheel-2.0-1.dist-info"
    result.did_create(distinfo)

    # Test install without --target
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--python-version",
        "3",
        "--platform",
        "fakeplat",
        "--abi",
        "fakeabi",
        "simplewheel",
        expect_error=True,
    )
    assert result.returncode == ERROR


def test_install_nonlocal_compatible_wheel_path(
    script: PipTestEnvironment,
    data: TestData,
    resolver_variant: ResolverVariant,
) -> None:
    target_dir = script.scratch_path / "target"

    # Test a full path requirement
    result = script.pip(
        "install",
        "-t",
        target_dir,
        "--no-index",
        "--only-binary=:all:",
        Path(data.packages) / "simplewheel-2.0-py3-fakeabi-fakeplat.whl",
        expect_error=(resolver_variant == "2020-resolver"),
    )
    if resolver_variant == "2020-resolver":
        assert result.returncode == ERROR
    else:
        assert result.returncode == SUCCESS

        distinfo = Path("scratch") / "target" / "simplewheel-2.0.dist-info"
        result.did_create(distinfo)

    # Test a full path requirement (without --target)
    result = script.pip(
        "install",
        "--no-index",
        "--only-binary=:all:",
        Path(data.packages) / "simplewheel-2.0-py3-fakeabi-fakeplat.whl",
        expect_error=True,
    )
    assert result.returncode == ERROR


@pytest.mark.parametrize("opt", ("--target", "--prefix"))
def test_install_with_target_or_prefix_and_scripts_no_warning(
    opt: str, script: PipTestEnvironment
) -> None:
    """
    Test that installing with --target does not trigger the "script not
    in PATH" warning (issue #5201)
    """
    target_dir = script.scratch_path / "target"
    pkga_path = script.scratch_path / "pkga"
    pkga_path.mkdir()
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              py_modules=["pkga"],
              entry_points={
                  'console_scripts': ['pkga=pkga:main']
              }
        )
    """
        )
    )
    pkga_path.joinpath("pkga.py").write_text(
        textwrap.dedent(
            """
        def main(): pass
    """
        )
    )
    result = script.pip("install", opt, target_dir, pkga_path)
    # This assertion isn't actually needed, if we get the script warning
    # the script.pip() call will fail with "stderr not expected". But we
    # leave the assertion to make the intention of the code clearer.
    assert "--no-warn-script-location" not in result.stderr, str(result)


def test_install_package_with_root(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test installing a package using pip install --root
    """
    root_dir = script.scratch_path / "root"
    result = script.pip(
        "install",
        "--root",
        root_dir,
        "-f",
        data.find_links,
        "--no-index",
        "simple==1.0",
    )
    normal_install_path = os.fspath(
        script.base_path / script.site_packages / "simple-1.0.dist-info"
    )
    # use a function borrowed from distutils
    # to change the root exactly how the --root option does it
    from pip._internal.locations.base import change_root

    root_path = change_root(os.path.join(script.scratch, "root"), normal_install_path)
    result.did_create(root_path)

    # Should show find-links location in output
    assert "Looking in indexes: " not in result.stdout
    assert "Looking in links: " in result.stdout


def test_install_package_with_prefix(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing a package using pip install --prefix
    """
    prefix_path = script.scratch_path / "prefix"
    result = script.pip(
        "install",
        "--prefix",
        prefix_path,
        "-f",
        data.find_links,
        "--no-binary",
        "simple",
        "--no-index",
        "simple==1.0",
    )

    rel_prefix_path = script.scratch / "prefix"
    install_path = join(
        sysconfig.get_path("purelib", vars={"base": rel_prefix_path}),
        "simple-1.0.dist-info",
    )
    result.did_create(install_path)


def _test_install_editable_with_prefix(
    script: PipTestEnvironment, files: Dict[str, str]
) -> None:
    # make a dummy project
    pkga_path = script.scratch_path / "pkga"
    pkga_path.mkdir()

    for fn, contents in files.items():
        pkga_path.joinpath(fn).write_text(textwrap.dedent(contents))

    if hasattr(sys, "pypy_version_info"):
        site_packages = os.path.join(
            "prefix", "lib", f"python{pyversion}", "site-packages"
        )
    else:
        site_packages = sysconfig.get_path("purelib", vars={"base": "prefix"})

    # make sure target path is in PYTHONPATH
    pythonpath = script.scratch_path / site_packages
    pythonpath.mkdir(parents=True)
    script.environ["PYTHONPATH"] = pythonpath

    # install pkga package into the absolute prefix directory
    prefix_path = script.scratch_path / "prefix"
    result = script.pip("install", "--editable", pkga_path, "--prefix", prefix_path)

    # assert pkga is installed at correct location
    install_path = script.scratch / site_packages / "pkga.egg-link"
    result.did_create(install_path)


@pytest.mark.network
def test_install_editable_with_target(script: PipTestEnvironment) -> None:
    pkg_path = script.scratch_path / "pkg"
    pkg_path.mkdir()
    pkg_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(
            name='pkg',
            install_requires=['watching_testrunner']
        )
    """
        )
    )

    target = script.scratch_path / "target"
    target.mkdir()
    result = script.pip("install", "--editable", pkg_path, "--target", target)

    result.did_create(script.scratch / "target" / "pkg.egg-link")
    result.did_create(script.scratch / "target" / "watching_testrunner.py")


def test_install_editable_with_prefix_setup_py(script: PipTestEnvironment) -> None:
    setup_py = """
from setuptools import setup
setup(name='pkga', version='0.1')
"""
    _test_install_editable_with_prefix(script, {"setup.py": setup_py})


@pytest.mark.skipif(
    sys.version_info >= (3, 12),
    reason="Setuptools<64 does not support Python 3.12+",
)
@pytest.mark.network
def test_install_editable_legacy_with_prefix_setup_cfg(
    script: PipTestEnvironment,
) -> None:
    setup_cfg = """[metadata]
name = pkga
version = 0.1
"""
    pyproject_toml = """[build-system]
requires = ["setuptools<64", "wheel"]
build-backend = "setuptools.build_meta"
"""
    _test_install_editable_with_prefix(
        script, {"setup.cfg": setup_cfg, "pyproject.toml": pyproject_toml}
    )


def test_install_package_conflict_prefix_and_user(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing a package using pip install --prefix --user errors out
    """
    prefix_path = script.scratch_path / "prefix"
    result = script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "--user",
        "--prefix",
        prefix_path,
        "simple==1.0",
        expect_error=True,
        quiet=True,
    )
    assert "Can not combine '--user' and '--prefix'" in result.stderr


def test_install_package_that_emits_unicode(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Install a package with a setup.py that emits UTF-8 output and then fails.

    Refs https://github.com/pypa/pip/issues/326
    """
    to_install = data.packages.joinpath("BrokenEmitsUTF8")
    result = script.pip(
        "install",
        to_install,
        expect_error=True,
        expect_temp=True,
        quiet=True,
    )
    assert (
        "FakeError: this package designed to fail on install" in result.stderr
    ), f"stderr: {result.stderr}"
    assert "UnicodeDecodeError" not in result.stderr
    assert "UnicodeDecodeError" not in result.stdout


def test_install_package_with_utf8_setup(
    script: PipTestEnvironment, data: TestData
) -> None:
    """Install a package with a setup.py that declares a utf-8 encoding."""
    to_install = data.packages.joinpath("SetupPyUTF8")
    script.pip("install", to_install)


def test_install_package_with_latin1_setup(
    script: PipTestEnvironment, data: TestData
) -> None:
    """Install a package with a setup.py that declares a latin-1 encoding."""
    to_install = data.packages.joinpath("SetupPyLatin1")
    script.pip("install", to_install)


def test_url_req_case_mismatch_no_index(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages contains Upper-1.0.tar.gz and Upper-2.0.tar.gz
    'requiresupper' has install_requires = ['upper']
    """
    Upper = "/".join((data.find_links, "Upper-1.0.tar.gz"))
    result = script.pip(
        "install", "--no-index", "-f", data.find_links, Upper, "requiresupper"
    )

    # only Upper-1.0.tar.gz should get installed.
    dist_info_folder = script.site_packages / "Upper-1.0.dist-info"
    result.did_create(dist_info_folder)
    dist_info_folder = script.site_packages / "Upper-2.0.dist-info"
    result.did_not_create(dist_info_folder)


def test_url_req_case_mismatch_file_index(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages3 contains Dinner-1.0.tar.gz and Dinner-2.0.tar.gz
    'requiredinner' has install_requires = ['dinner']

    This test is similar to test_url_req_case_mismatch_no_index; that test
    tests behaviour when using "--no-index -f", while this one does the same
    test when using "--index-url". Unfortunately this requires a different
    set of packages as it requires a prepared index.html file and
    subdirectory-per-package structure.
    """
    Dinner = "/".join((data.find_links3, "dinner", "Dinner-1.0.tar.gz"))
    result = script.pip(
        "install", "--index-url", data.find_links3, Dinner, "requiredinner"
    )

    # only Upper-1.0.tar.gz should get installed.
    dist_info_folder = script.site_packages / "Dinner-1.0.dist-info"
    result.did_create(dist_info_folder)
    dist_info_folder = script.site_packages / "Dinner-2.0.dist-info"
    result.did_not_create(dist_info_folder)


def test_url_incorrect_case_no_index(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Same as test_url_req_case_mismatch_no_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "upper",
    )

    # only Upper-2.0.tar.gz should get installed.
    dist_info_folder = script.site_packages / "Upper-1.0.dist-info"
    result.did_not_create(dist_info_folder)
    dist_info_folder = script.site_packages / "Upper-2.0.dist-info"
    result.did_create(dist_info_folder)


def test_url_incorrect_case_file_index(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Same as test_url_req_case_mismatch_file_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        "install",
        "--index-url",
        data.find_links3,
        "dinner",
        expect_stderr=True,
    )

    # only Upper-2.0.tar.gz should get installed.
    dist_info_folder = script.site_packages / "Dinner-1.0.dist-info"
    result.did_not_create(dist_info_folder)
    dist_info_folder = script.site_packages / "Dinner-2.0.dist-info"
    result.did_create(dist_info_folder)

    # Should show index-url location in output
    assert "Looking in indexes: " in result.stdout
    assert "Looking in links: " not in result.stdout


@pytest.mark.network
def test_compiles_pyc(script: PipTestEnvironment) -> None:
    """
    Test installing with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
        *script.site_packages_path.glob("initools/__pycache__/__init__*.pyc"),
    ]

    assert any(exists)


@pytest.mark.network
def test_no_compiles_pyc(script: PipTestEnvironment) -> None:
    """
    Test installing from wheel with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--no-compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
        *script.site_packages_path.glob("initools/__pycache__/__init__*.pyc"),
    ]

    assert not any(exists)


def test_install_upgrade_editable_depending_on_other_editable(
    script: PipTestEnvironment,
) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """
        )
    )
    script.pip("install", "--editable", pkga_path)
    result = script.pip("list", "--format=freeze")
    assert "pkga==0.1" in result.stdout

    script.scratch_path.joinpath("pkgb").mkdir()
    pkgb_path = script.scratch_path / "pkgb"
    pkgb_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkgb',
              version='0.1',
              install_requires=['pkga'])
    """
        )
    )
    script.pip("install", "--upgrade", "--editable", pkgb_path, "--no-index")
    result = script.pip("list", "--format=freeze")
    assert "pkgb==0.1" in result.stdout


def test_install_subprocess_output_handling(
    script: PipTestEnvironment, data: TestData
) -> None:
    args = ["install", os.fspath(data.src.joinpath("chattymodule"))]

    # Regular install should not show output from the chatty setup.py
    result = script.pip(*args)
    assert 0 == result.stdout.count("HELLO FROM CHATTYMODULE")
    script.pip("uninstall", "-y", "chattymodule")

    # With --verbose we should show the output.
    # Only count examples with sys.argv[1] == egg_info, because we call
    # setup.py multiple times, which should not count as duplicate output.
    result = script.pip(*(args + ["--verbose"]), expect_stderr=True)
    assert 1 == result.stderr.count("HELLO FROM CHATTYMODULE egg_info")
    script.pip("uninstall", "-y", "chattymodule")

    # If the install fails, then we *should* show the output... but only once,
    # even if --verbose is given.
    result = script.pip(*(args + ["--global-option=--fail"]), expect_error=True)
    # This error is emitted 3 times:
    # - by setup.py bdist_wheel
    # - by setup.py clean
    assert 2 == result.stderr.count("I DIE, I DIE")

    result = script.pip(
        *(args + ["--global-option=--fail", "--verbose"]), expect_error=True
    )
    assert 2 == result.stderr.count("I DIE, I DIE")


def test_install_log(script: PipTestEnvironment, data: TestData, tmpdir: Path) -> None:
    # test that verbose logs go to "--log" file
    f = tmpdir.joinpath("log.txt")
    result = script.pip(f"--log={f}", "install", data.src.joinpath("chattymodule"))
    assert 0 == result.stdout.count("HELLO FROM CHATTYMODULE")
    with open(f) as fp:
        # one from egg_info, one from install
        assert 2 == fp.read().count("HELLO FROM CHATTYMODULE")


def test_install_topological_sort(script: PipTestEnvironment, data: TestData) -> None:
    res = str(script.pip("install", "TopoRequires4", "--no-index", "-f", data.packages))
    order1 = "TopoRequires, TopoRequires2, TopoRequires3, TopoRequires4"
    order2 = "TopoRequires, TopoRequires3, TopoRequires2, TopoRequires4"
    assert order1 in res or order2 in res, res


def test_cleanup_after_failed_wheel(script: PipTestEnvironment) -> None:
    res = script.pip_install_local("wheelbrokenafter", expect_error=True)
    assert "ERROR: Failed building wheel for wheelbrokenafter" in res.stderr
    # OK, assert that we *said* we were cleaning up:
    # /!\ if in need to change this, also change test_pep517_no_legacy_cleanup
    assert "Running setup.py clean for wheelbrokenafter" in str(res), str(res)


def test_install_builds_wheels(script: PipTestEnvironment, data: TestData) -> None:
    # We need to use a subprocess to get the right value on Windows.
    res = script.run(
        "python",
        "-c",
        (
            "from pip._internal.utils import appdirs; "
            'print(appdirs.user_cache_dir("pip"))'
        ),
    )
    wheels_cache = os.path.join(res.stdout.rstrip("\n"), "wheels")
    # NB This incidentally tests a local tree + tarball inputs
    # see test_install_editable_from_git_autobuild_wheel for editable
    # vcs coverage.
    to_install = data.packages.joinpath("requires_wheelbroken_upper")
    res = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        to_install,
        expect_error=True,  # error building wheelbroken
    )
    wheels: List[str] = []
    for _, _, files in os.walk(wheels_cache):
        wheels.extend(f for f in files if f.endswith(".whl"))
    # Built wheel for upper
    assert "Building wheel for upper" in str(res), str(res)
    # Built wheel for wheelbroken, but failed
    assert "Building wheel for wheelb" in str(res), str(res)
    assert "Failed to build wheelbroken" in str(res), str(res)
    # Wheels are built for local directories, but not cached.
    assert "Building wheel for requir" in str(res), str(res)
    # into the cache
    assert wheels != [], str(res)
    assert wheels == [
        "Upper-2.0-py{}-none-any.whl".format(sys.version_info[0]),
    ]


def test_install_no_binary_builds_wheels(
    script: PipTestEnvironment, data: TestData
) -> None:
    to_install = data.packages.joinpath("requires_wheelbroken_upper")
    res = script.pip(
        "install",
        "--no-index",
        "--no-binary=upper",
        "-f",
        data.find_links,
        to_install,
        expect_error=True,  # error building wheelbroken
    )
    # Wheels are built for all requirements
    assert "Building wheel for wheelb" in str(res), str(res)
    assert "Building wheel for requir" in str(res), str(res)
    assert "Building wheel for upper" in str(res), str(res)
    # Wheelbroken failed to build
    assert "Failed to build wheelbroken" in str(res), str(res)


@pytest.mark.network
def test_install_no_binary_builds_pep_517_wheel(
    script: PipTestEnvironment, data: TestData
) -> None:
    to_install = data.packages.joinpath("pep517_setup_and_pyproject")
    res = script.pip("install", "--no-binary=:all:", "-f", data.find_links, to_install)
    expected = "Successfully installed pep517-setup-and-pyproject"
    # Must have installed the package
    assert expected in str(res), str(res)

    assert "Building wheel for pep517-setup" in str(res), str(res)


@pytest.mark.network
def test_install_no_binary_uses_local_backend(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    to_install = data.packages.joinpath("pep517_wrapper_buildsys")
    script.environ["PIP_TEST_MARKER_FILE"] = marker = str(tmpdir / "marker")
    res = script.pip("install", "--no-binary=:all:", "-f", data.find_links, to_install)
    expected = "Successfully installed pep517-wrapper-buildsys"
    # Must have installed the package
    assert expected in str(res), str(res)

    assert os.path.isfile(marker), "Local PEP 517 backend not used"


def test_install_no_binary_uses_cached_wheels(
    script: PipTestEnvironment, data: TestData
) -> None:
    # Seed the cache
    script.pip("install", "--no-index", "-f", data.find_links, "upper")
    script.pip("uninstall", "upper", "-y")
    res = script.pip(
        "install",
        "--no-index",
        "--no-binary=:all:",
        "-f",
        data.find_links,
        "upper",
        expect_stderr=True,
    )
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # upper is built and not obtained from cache
    assert "Building wheel for upper" not in str(res), str(res)


def test_install_editable_with_wrong_egg_name(
    script: PipTestEnvironment, resolver_variant: ResolverVariant
) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """
        )
    )
    result = script.pip(
        "install",
        "--editable",
        f"file://{pkga_path}#egg=pkgb",
        expect_error=(resolver_variant == "2020-resolver"),
    )
    assert (
        "Generating metadata for package pkgb produced metadata "
        "for project name pkga. Fix your #egg=pkgb "
        "fragments."
    ) in result.stderr
    if resolver_variant == "2020-resolver":
        assert "has inconsistent" in result.stdout, str(result)
    else:
        assert "Successfully installed pkga" in str(result), str(result)


def test_install_tar_xz(script: PipTestEnvironment, data: TestData) -> None:
    try:
        import lzma  # noqa
    except ImportError:
        pytest.skip("No lzma support")
    res = script.pip("install", data.packages / "singlemodule-0.0.1.tar.xz")
    assert "Successfully installed singlemodule-0.0.1" in res.stdout, res


def test_install_tar_lzma(script: PipTestEnvironment, data: TestData) -> None:
    try:
        import lzma  # noqa
    except ImportError:
        pytest.skip("No lzma support")
    res = script.pip("install", data.packages / "singlemodule-0.0.1.tar.lzma")
    assert "Successfully installed singlemodule-0.0.1" in res.stdout, res


def test_double_install(script: PipTestEnvironment) -> None:
    """
    Test double install passing with two same version requirements
    """
    result = script.pip("install", "pip", "pip")
    msg = "Double requirement given: pip (already in pip, name='pip')"
    assert msg not in result.stderr


def test_double_install_fail(
    script: PipTestEnvironment, resolver_variant: ResolverVariant
) -> None:
    """
    Test double install failing with two different version requirements
    """
    result = script.pip(
        "install",
        "pip==7.*",
        "pip==7.1.2",
        # The new resolver is perfectly capable of handling this
        expect_error=(resolver_variant == "legacy"),
    )
    if resolver_variant == "legacy":
        msg = "Double requirement given: pip==7.1.2 (already in pip==7.*, name='pip')"
        assert msg in result.stderr


def _get_expected_error_text() -> str:
    return ("Package 'pkga' requires a different Python: {} not in '<1.0'").format(
        ".".join(map(str, sys.version_info[:3]))
    )


def test_install_incompatible_python_requires(script: PipTestEnvironment) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """
        )
    )
    result = script.pip("install", pkga_path, expect_error=True)
    assert _get_expected_error_text() in result.stderr, str(result)


def test_install_incompatible_python_requires_editable(
    script: PipTestEnvironment,
) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """
        )
    )
    result = script.pip("install", f"--editable={pkga_path}", expect_error=True)
    assert _get_expected_error_text() in result.stderr, str(result)


def test_install_incompatible_python_requires_wheel(script: PipTestEnvironment) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """
        )
    )
    script.run(
        "python",
        "setup.py",
        "bdist_wheel",
        "--universal",
        cwd=pkga_path,
    )
    result = script.pip(
        "install", "./pkga/dist/pkga-0.1-py2.py3-none-any.whl", expect_error=True
    )
    assert _get_expected_error_text() in result.stderr, str(result)


def test_install_compatible_python_requires(script: PipTestEnvironment) -> None:
    script.scratch_path.joinpath("pkga").mkdir()
    pkga_path = script.scratch_path / "pkga"
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              python_requires='>1.0',
              version='0.1')
    """
        )
    )
    res = script.pip("install", pkga_path)
    assert "Successfully installed pkga-0.1" in res.stdout, res


@pytest.mark.network
def test_install_pep508_with_url(script: PipTestEnvironment) -> None:
    res = script.pip(
        "install",
        "--no-index",
        "packaging@https://files.pythonhosted.org/packages/2f/2b/"
        "c681de3e1dbcd469537aefb15186b800209aa1f299d933d23b48d85c9d56/"
        "packaging-15.3-py2.py3-none-any.whl#sha256="
        "ce1a869fe039fbf7e217df36c4653d1dbe657778b2d41709593a0003584405f4",
    )
    assert "Successfully installed packaging-15.3" in str(res), str(res)


@pytest.mark.network
def test_install_pep508_with_url_in_install_requires(
    script: PipTestEnvironment,
) -> None:
    pkga_path = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        install_requires=[
            "packaging@https://files.pythonhosted.org/packages/2f/2b/"
            "c681de3e1dbcd469537aefb15186b800209aa1f299d933d23b48d85c9d56/"
            "packaging-15.3-py2.py3-none-any.whl#sha256="
            "ce1a869fe039fbf7e217df36c4653d1dbe657778b2d41709593a0003584405f4"
        ],
    )
    res = script.pip("install", pkga_path)
    assert "Successfully installed packaging-15.3" in str(res), str(res)


@pytest.mark.network
@pytest.mark.parametrize("index", (PyPI.simple_url, TestPyPI.simple_url))
def test_install_from_test_pypi_with_ext_url_dep_is_blocked(
    script: PipTestEnvironment, index: str
) -> None:
    res = script.pip(
        "install",
        "--index-url",
        index,
        "pep-508-url-deps",
        expect_error=True,
    )
    error_message = (
        "Packages installed from PyPI cannot depend on packages "
        "which are not also hosted on PyPI."
    )
    error_cause = (
        "pep-508-url-deps depends on sampleproject@ "
        "https://github.com/pypa/sampleproject/archive/master.zip"
    )
    assert res.returncode == 1
    assert error_message in res.stderr, str(res)
    assert error_cause in res.stderr, str(res)


@pytest.mark.xfail(
    reason="No longer possible to trigger the warning with either --prefix or --target"
)
def test_installing_scripts_outside_path_prints_warning(
    script: PipTestEnvironment,
) -> None:
    result = script.pip_install_local("--prefix", script.scratch_path, "script_wheel1")
    assert "Successfully installed script_wheel1" in result.stdout, str(result)
    assert "--no-warn-script-location" in result.stderr


def test_installing_scripts_outside_path_can_suppress_warning(
    script: PipTestEnvironment,
) -> None:
    result = script.pip_install_local(
        "--prefix", script.scratch_path, "--no-warn-script-location", "script_wheel1"
    )
    assert "Successfully installed script_wheel1" in result.stdout, str(result)
    assert "--no-warn-script-location" not in result.stderr


def test_installing_scripts_on_path_does_not_print_warning(
    script: PipTestEnvironment,
) -> None:
    result = script.pip_install_local("script_wheel1")
    assert "Successfully installed script_wheel1" in result.stdout, str(result)
    assert "--no-warn-script-location" not in result.stderr


def test_install_conflict_results_in_warning(
    script: PipTestEnvironment, data: TestData
) -> None:
    pkgA_path = create_test_package_with_setup(
        script,
        name="pkgA",
        version="1.0",
        install_requires=["pkgb == 1.0"],
    )
    pkgB_path = create_test_package_with_setup(
        script,
        name="pkgB",
        version="2.0",
    )

    # Install pkgA without its dependency
    result1 = script.pip("install", "--no-index", pkgA_path, "--no-deps")
    assert "Successfully installed pkgA-1.0" in result1.stdout, str(result1)

    # Then install an incorrect version of the dependency
    result2 = script.pip(
        "install",
        "--no-index",
        pkgB_path,
        allow_stderr_error=True,
    )
    assert "pkga 1.0 requires pkgb==1.0" in result2.stderr, str(result2)
    assert "Successfully installed pkgB-2.0" in result2.stdout, str(result2)


def test_install_conflict_warning_can_be_suppressed(
    script: PipTestEnvironment, data: TestData
) -> None:
    pkgA_path = create_test_package_with_setup(
        script,
        name="pkgA",
        version="1.0",
        install_requires=["pkgb == 1.0"],
    )
    pkgB_path = create_test_package_with_setup(
        script,
        name="pkgB",
        version="2.0",
    )

    # Install pkgA without its dependency
    result1 = script.pip("install", "--no-index", pkgA_path, "--no-deps")
    assert "Successfully installed pkgA-1.0" in result1.stdout, str(result1)

    # Then install an incorrect version of the dependency; suppressing warning
    result2 = script.pip("install", "--no-index", pkgB_path, "--no-warn-conflicts")
    assert "Successfully installed pkgB-2.0" in result2.stdout, str(result2)


def test_target_install_ignores_distutils_config_install_prefix(
    script: PipTestEnvironment,
) -> None:
    prefix = script.scratch_path / "prefix"
    distutils_config = Path.home().joinpath(
        "pydistutils.cfg" if sys.platform == "win32" else ".pydistutils.cfg",
    )
    distutils_config.write_text(
        textwrap.dedent(
            f"""
        [install]
        prefix={prefix}
        """
        )
    )
    target = script.scratch_path / "target"
    result = script.pip_install_local("simplewheel", "-t", target)

    assert "Successfully installed simplewheel" in result.stdout

    relative_target = os.path.relpath(target, script.base_path)
    relative_script_base = os.path.relpath(prefix, script.base_path)
    result.did_create(relative_target)
    result.did_not_create(relative_script_base)


@pytest.mark.usefixtures("enable_user_site")
def test_user_config_accepted(script: PipTestEnvironment) -> None:
    # user set in the config file is parsed as 0/1 instead of True/False.
    # Check that this doesn't cause a problem.
    config_file = script.scratch_path / "pip.conf"
    script.environ["PIP_CONFIG_FILE"] = str(config_file)
    config_file.write_text("[install]\nuser = true")
    result = script.pip_install_local("simplewheel")

    assert "Successfully installed simplewheel" in result.stdout

    relative_user = os.path.relpath(script.user_site_path, script.base_path)
    result.did_create(join(relative_user, "simplewheel"))


@pytest.mark.parametrize(
    "install_args, expected_message",
    [
        ([], "Requirement already satisfied: pip"),
        (["--upgrade"], "Requirement already {}: pip in"),
    ],
)
@pytest.mark.parametrize("use_module", [True, False])
def test_install_pip_does_not_modify_pip_when_satisfied(
    script: PipTestEnvironment,
    install_args: List[str],
    expected_message: str,
    use_module: bool,
    resolver_variant: ResolverVariant,
) -> None:
    """
    Test it doesn't upgrade the pip if it already satisfies the requirement.
    """
    variation = "satisfied" if resolver_variant else "up-to-date"
    expected_message = expected_message.format(variation)
    result = script.pip_install_local("pip", *install_args, use_module=use_module)
    assert expected_message in result.stdout, str(result)


def test_ignore_yanked_file(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test ignore a "yanked" file.
    """
    result = script.pip(
        "install",
        "simple",
        "--index-url",
        data.index_url("yanked"),
    )
    # Make sure a "yanked" release is ignored
    assert "Successfully installed simple-2.0\n" in result.stdout, str(result)


def test_invalid_index_url_argument(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """
    Test the behaviour of an invalid --index-url argument
    """

    result = script.pip(
        "install",
        "--index-url",
        "--user",
        shared_data.find_links3,
        "Dinner",
        expect_error=True,
    )

    assert (
        'WARNING: The index url "--user" seems invalid, please provide a scheme.'
    ) in result.stderr, str(result)


def test_valid_index_url_argument(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """
    Test the behaviour of an valid --index-url argument
    """

    result = script.pip("install", "--index-url", shared_data.find_links3, "Dinner")

    assert "Successfully installed Dinner" in result.stdout, str(result)


def test_install_yanked_file_and_print_warning(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test install a "yanked" file and print a warning.

    Yanked files are always ignored, unless they are the only file that
    matches a version specifier that "pins" to an exact version (PEP 592).
    """
    result = script.pip(
        "install",
        "simple==3.0",
        "--index-url",
        data.index_url("yanked"),
        expect_stderr=True,
    )
    expected_warning = "Reason for being yanked: test reason message"
    assert expected_warning in result.stderr, str(result)
    # Make sure a "yanked" release is installed
    assert "Successfully installed simple-3.0\n" in result.stdout, str(result)


def test_error_all_yanked_files_and_no_pin(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test raising an error if there are only "yanked" files available and no pin
    """
    result = script.pip(
        "install",
        "simple",
        "--index-url",
        data.index_url("yanked_all"),
        expect_error=True,
    )
    # Make sure an error is raised
    assert (
        result.returncode == 1
        and "ERROR: No matching distribution found for simple\n" in result.stderr
    ), str(result)


@pytest.mark.skipif(
    sys.platform == "linux" and sys.version_info < (3, 8),
    reason="Custom SSL certification not running well in CI",
)
@pytest.mark.parametrize(
    "install_args",
    [
        (),
        ("--trusted-host", "localhost"),
    ],
)
def test_install_sends_client_cert(
    install_args: Tuple[str, ...],
    script: PipTestEnvironment,
    cert_factory: CertFactory,
    data: TestData,
) -> None:
    cert_path = cert_factory()
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(cert_path, cert_path)
    ctx.load_verify_locations(cafile=cert_path)
    ctx.verify_mode = ssl.CERT_REQUIRED

    server = make_mock_server(ssl_context=ctx)
    server.mock.side_effect = [
        package_page(
            {
                "simple-3.0.tar.gz": "/files/simple-3.0.tar.gz",
            }
        ),
        file_response(data.packages / "simple-3.0.tar.gz"),
    ]

    url = f"https://{server.host}:{server.port}/simple"

    args = ["install", "-vvv", "--cert", cert_path, "--client-cert", cert_path]
    args.extend(["--index-url", url])
    args.extend(install_args)
    args.append("simple")

    with server_running(server):
        script.pip(*args)

    assert server.mock.call_count == 2
    for call_args in server.mock.call_args_list:
        # Legacy: replace call_args[0] with call_args.args
        # when pip drops support for python3.7
        environ, _ = call_args[0]
        assert "SSL_CLIENT_CERT" in environ
        assert environ["SSL_CLIENT_CERT"]


def test_install_skip_work_dir_pkg(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that install of a package in working directory
    should pass on the second attempt after an install
    and an uninstall
    """

    # Create a test package, install it and then uninstall it
    pkg_path = create_test_package_with_setup(script, name="simple", version="1.0")
    script.pip("install", "-e", ".", expect_stderr=True, cwd=pkg_path)

    script.pip("uninstall", "simple", "-y")

    # Running the install command again from the working directory
    # will install the package as it was uninstalled earlier
    result = script.pip(
        "install",
        "--find-links",
        data.find_links,
        "simple",
        expect_stderr=True,
        cwd=pkg_path,
    )

    assert "Requirement already satisfied: simple" not in result.stdout
    assert "Successfully installed simple" in result.stdout


@pytest.mark.parametrize(
    "package_name", ("simple-package", "simple_package", "simple.package")
)
def test_install_verify_package_name_normalization(
    script: PipTestEnvironment, package_name: str
) -> None:
    """
    Test that install of a package again using a name which
    normalizes to the original package name, is a no-op
    since the package is already installed
    """
    pkg_path = create_test_package_with_setup(
        script, name="simple-package", version="1.0"
    )
    result = script.pip("install", "-e", ".", expect_stderr=True, cwd=pkg_path)
    assert "Successfully installed simple-package" in result.stdout

    result = script.pip("install", package_name)
    assert "Requirement already satisfied: {}".format(package_name) in result.stdout


def test_install_logs_pip_version_in_debug(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    fake_package = shared_data.packages / "simple-2.0.tar.gz"
    result = script.pip("install", "-v", fake_package)
    pattern = "Using pip .* from .*"
    assert_re_match(pattern, result.stdout)


def install_find_links(
    script: PipTestEnvironment,
    data: TestData,
    args: Iterable[str],
    *,
    dry_run: bool,
    target_dir: Optional[Path],
) -> TestPipResult:
    return script.pip(
        "install",
        *(
            (
                "--target",
                str(target_dir),
            )
            if target_dir is not None
            else ()
        ),
        *(("--dry-run",) if dry_run else ()),
        "--no-index",
        "--find-links",
        data.find_links,
        *args,
    )


@pytest.mark.parametrize(
    "with_target_dir",
    (True, False),
)
def test_install_dry_run_nothing_installed(
    script: PipTestEnvironment,
    data: TestData,
    tmpdir: Path,
    with_target_dir: bool,
) -> None:
    """Test that pip install --dry-run logs what it would install, but doesn't actually
    install anything."""
    if with_target_dir:
        install_dir = tmpdir / "fake-install"
        install_dir.mkdir()
    else:
        install_dir = None

    result = install_find_links(
        script, data, ["simple"], dry_run=True, target_dir=install_dir
    )
    assert "Would install simple-3.0" in result.stdout
    assert "Successfully installed" not in result.stdout

    script.assert_not_installed("simple")
    if with_target_dir:
        assert not os.listdir(install_dir)

    # Ensure that the same install command would normally have worked if not for
    # --dry-run.
    install_find_links(script, data, ["simple"], dry_run=False, target_dir=install_dir)
    if with_target_dir:
        assert os.listdir(install_dir)
    else:
        script.assert_installed(simple="3.0")


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="3.11 required to find distributions via importlib metadata",
)
def test_install_existing_memory_distribution(script: PipTestEnvironment) -> None:
    sitecustomize_text = textwrap.dedent(
        """
        import sys
        from importlib.metadata import Distribution, DistributionFinder


        EXAMPLE_METADATA = '''Metadata-Version: 2.1
        Name: example
        Version: 1.0.0

        '''

        class ExampleDistribution(Distribution):
            def locate_file(self, path):
                return path

            def read_text(self, filename):
                if filename == 'METADATA':
                    return EXAMPLE_METADATA


        class CustomFinder(DistributionFinder):
            def find_distributions(self, context=None):
                return [ExampleDistribution()]


        sys.meta_path.append(CustomFinder())
        """
    )
    with open(script.site_packages_path / "sitecustomize.py", "w") as sitecustomize:
        sitecustomize.write(sitecustomize_text)

    result = script.pip("install", "example")

    assert "Requirement already satisfied: example in <memory>" in result.stdout


def test_install_pip_prints_req_chain_local(script: PipTestEnvironment) -> None:
    """
    Test installing a local package with a dependency and check that the
    dependency chain is reported.
    """

    req_path = script.scratch_path.joinpath("requirements.txt")
    req_path.write_text("base==0.1.0")

    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    dep_path = create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-r",
        req_path,
    )
    assert_re_match(
        rf"Processing .*{re.escape(os.path.basename(dep_path))} "
        rf"\(from base==0.1.0->-r {re.escape(str(req_path))} \(line 1\)\)",
        result.stdout,
    )


@pytest.mark.network
def test_install_pip_prints_req_chain_pypi(script: PipTestEnvironment) -> None:
    """
    Test installing a package with a dependency from PyPI and check that the
    dependency chain is reported.
    """
    req_path = script.scratch_path.joinpath("requirements.txt")
    req_path.write_text("Paste[openid]==1.7.5.1")

    result = script.pip(
        "install",
        "-r",
        req_path,
    )

    assert (
        f"Collecting python-openid "
        f"(from Paste[openid]==1.7.5.1->-r {req_path} (line 1))" in result.stdout
    )
