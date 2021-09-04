import logging
import os
import sys
import textwrap
from os.path import join, normpath
from tempfile import mkdtemp
from unittest.mock import Mock

import pytest

from pip._internal.req.constructors import install_req_from_line
from pip._internal.utils.misc import rmtree
from tests.lib import assert_all_changes, create_test_package_with_setup, need_svn
from tests.lib.local_repos import local_checkout, local_repo


@pytest.mark.network
def test_basic_uninstall(script):
    """
    Test basic install and uninstall.

    """
    result = script.pip("install", "INITools==0.2")
    result.did_create(join(script.site_packages, "initools"))
    # the import forces the generation of __pycache__ if the version of python
    # supports it
    script.run("python", "-c", "import initools")
    result2 = script.pip("uninstall", "INITools", "-y")
    assert_all_changes(result, result2, [script.venv / "build", "cache"])


def test_basic_uninstall_distutils(script):
    """
    Test basic install and uninstall.

    """
    script.scratch_path.joinpath("distutils_install").mkdir()
    pkg_path = script.scratch_path / "distutils_install"
    pkg_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from distutils.core import setup
        setup(
            name='distutils-install',
            version='0.1',
        )
    """
        )
    )
    result = script.run("python", pkg_path / "setup.py", "install")
    result = script.pip("list", "--format=json")
    script.assert_installed(distutils_install="0.1")
    result = script.pip(
        "uninstall", "distutils_install", "-y", expect_stderr=True, expect_error=True
    )
    assert (
        "Cannot uninstall 'distutils-install'. It is a distutils installed "
        "project and thus we cannot accurately determine which files belong "
        "to it which would lead to only a partial uninstall."
    ) in result.stderr


@pytest.mark.network
def test_basic_uninstall_with_scripts(script):
    """
    Uninstall an easy_installed package with scripts.

    """
    # setuptools 52 removed easy_install.
    script.pip("install", "setuptools==51.3.3", use_module=True)

    result = script.easy_install("PyLogo", expect_stderr=True)
    easy_install_pth = script.site_packages / "easy-install.pth"
    pylogo = sys.platform == "win32" and "pylogo" or "PyLogo"
    assert pylogo in result.files_updated[easy_install_pth].bytes
    result2 = script.pip("uninstall", "pylogo", "-y")
    assert_all_changes(
        result,
        result2,
        [script.venv / "build", "cache", easy_install_pth],
    )


@pytest.mark.parametrize("name", ["GTrolls.tar.gz", "https://guyto.com/archives/"])
def test_uninstall_invalid_parameter(script, caplog, name):
    result = script.pip("uninstall", name, "-y", expect_error=True)
    expected_message = (
        f"Invalid requirement: '{name}' ignored -"
        f" the uninstall command expects named requirements."
    )
    assert expected_message in result.stderr


@pytest.mark.network
def test_uninstall_easy_install_after_import(script):
    """
    Uninstall an easy_installed package after it's been imported

    """
    # setuptools 52 removed easy_install.
    script.pip("install", "setuptools==51.3.3", use_module=True)

    result = script.easy_install("INITools==0.2", expect_stderr=True)
    # the import forces the generation of __pycache__ if the version of python
    # supports it
    script.run("python", "-c", "import initools")
    result2 = script.pip("uninstall", "INITools", "-y")
    assert_all_changes(
        result,
        result2,
        [
            script.venv / "build",
            "cache",
            script.site_packages / "easy-install.pth",
        ],
    )


@pytest.mark.network
def test_uninstall_trailing_newline(script):
    """
    Uninstall behaves appropriately if easy-install.pth
    lacks a trailing newline

    """
    # setuptools 52 removed easy_install.
    script.pip("install", "setuptools==51.3.3", use_module=True)

    script.easy_install("INITools==0.2", expect_stderr=True)
    script.easy_install("PyLogo", expect_stderr=True)
    easy_install_pth = script.site_packages_path / "easy-install.pth"

    # trim trailing newline from easy-install.pth
    with open(easy_install_pth) as f:
        pth_before = f.read()

    with open(easy_install_pth, "w") as f:
        f.write(pth_before.rstrip())

    # uninstall initools
    script.pip("uninstall", "INITools", "-y")
    with open(easy_install_pth) as f:
        pth_after = f.read()

    # verify that only initools is removed
    before_without_initools = [
        line for line in pth_before.splitlines() if "initools" not in line.lower()
    ]
    lines_after = pth_after.splitlines()

    assert lines_after == before_without_initools


@pytest.mark.network
def test_basic_uninstall_namespace_package(script):
    """
    Uninstall a distribution with a namespace package without clobbering
    the namespace and everything in it.

    """
    result = script.pip("install", "pd.requires==0.0.3")
    result.did_create(join(script.site_packages, "pd"))
    result2 = script.pip("uninstall", "pd.find", "-y")
    assert join(script.site_packages, "pd") not in result2.files_deleted, sorted(
        result2.files_deleted.keys()
    )
    assert join(script.site_packages, "pd", "find") in result2.files_deleted, sorted(
        result2.files_deleted.keys()
    )


def test_uninstall_overlapping_package(script, data):
    """
    Uninstalling a distribution that adds modules to a pre-existing package
    should only remove those added modules, not the rest of the existing
    package.

    See: GitHub issue #355 (pip uninstall removes things it didn't install)
    """
    parent_pkg = data.packages.joinpath("parent-0.1.tar.gz")
    child_pkg = data.packages.joinpath("child-0.1.tar.gz")

    result1 = script.pip("install", parent_pkg)
    result1.did_create(join(script.site_packages, "parent"))
    result2 = script.pip("install", child_pkg)
    result2.did_create(join(script.site_packages, "child"))
    result2.did_create(
        normpath(join(script.site_packages, "parent/plugins/child_plugin.py"))
    )
    # The import forces the generation of __pycache__ if the version of python
    #  supports it
    script.run("python", "-c", "import parent.plugins.child_plugin, child")
    result3 = script.pip("uninstall", "-y", "child")
    assert join(script.site_packages, "child") in result3.files_deleted, sorted(
        result3.files_created.keys()
    )
    assert (
        normpath(join(script.site_packages, "parent/plugins/child_plugin.py"))
        in result3.files_deleted
    ), sorted(result3.files_deleted.keys())
    assert join(script.site_packages, "parent") not in result3.files_deleted, sorted(
        result3.files_deleted.keys()
    )
    # Additional check: uninstalling 'child' should return things to the
    # previous state, without unintended side effects.
    assert_all_changes(result2, result3, [])


@pytest.mark.parametrize(
    "console_scripts", ["test_ = distutils_install", "test_:test_ = distutils_install"]
)
def test_uninstall_entry_point_colon_in_name(script, console_scripts):
    """
    Test uninstall package with two or more entry points in the same section,
    whose name contain a colon.
    """
    pkg_name = "ep_install"
    pkg_path = create_test_package_with_setup(
        script,
        name=pkg_name,
        version="0.1",
        entry_points={
            "console_scripts": [
                console_scripts,
            ],
            "pip_test.ep": [
                "ep:name1 = distutils_install",
                "ep:name2 = distutils_install",
            ],
        },
    )
    script_name = script.bin_path.joinpath(console_scripts.split("=")[0].strip())
    if sys.platform == "win32":
        script_name += ".exe"
    script.pip("install", pkg_path)
    assert script_name.exists()
    script.assert_installed(ep_install="0.1")

    script.pip("uninstall", "ep_install", "-y")
    assert not script_name.exists()
    script.assert_not_installed("ep-install")


def test_uninstall_gui_scripts(script):
    """
    Make sure that uninstall removes gui scripts
    """
    pkg_name = "gui_pkg"
    pkg_path = create_test_package_with_setup(
        script,
        name=pkg_name,
        version="0.1",
        entry_points={
            "gui_scripts": [
                "test_ = distutils_install",
            ],
        },
    )
    script_name = script.bin_path.joinpath("test_")
    if sys.platform == "win32":
        script_name += ".exe"
    script.pip("install", pkg_path)
    assert script_name.exists()
    script.pip("uninstall", pkg_name, "-y")
    assert not script_name.exists()


def test_uninstall_console_scripts(script):
    """
    Test uninstalling a package with more files (console_script entry points,
    extra directories).
    """
    pkg_path = create_test_package_with_setup(
        script,
        name="discover",
        version="0.1",
        entry_points={"console_scripts": ["discover = discover:main"]},
    )
    result = script.pip("install", pkg_path)
    result.did_create(script.bin / "discover" + script.exe)
    result2 = script.pip("uninstall", "discover", "-y")
    assert_all_changes(result, result2, [script.venv / "build", "cache"])


def test_uninstall_console_scripts_uppercase_name(script):
    """
    Test uninstalling console script with uppercase character.
    """
    pkg_path = create_test_package_with_setup(
        script,
        name="ep_install",
        version="0.1",
        entry_points={
            "console_scripts": [
                "Test = distutils_install",
            ],
        },
    )
    script_name = script.bin_path.joinpath("Test" + script.exe)

    script.pip("install", pkg_path)
    assert script_name.exists()

    script.pip("uninstall", "ep_install", "-y")
    assert not script_name.exists()


@pytest.mark.network
def test_uninstall_easy_installed_console_scripts(script):
    """
    Test uninstalling package with console_scripts that is easy_installed.
    """
    # setuptools 52 removed easy_install and prints a warning after 42 when
    # the command is used.
    script.pip("install", "setuptools==51.3.3", use_module=True)

    result = script.easy_install("discover", allow_stderr_warning=True)
    result.did_create(script.bin / "discover" + script.exe)
    result2 = script.pip("uninstall", "discover", "-y")
    assert_all_changes(
        result,
        result2,
        [
            script.venv / "build",
            "cache",
            script.site_packages / "easy-install.pth",
        ],
    )


@pytest.mark.xfail
@pytest.mark.network
@need_svn
def test_uninstall_editable_from_svn(script, tmpdir):
    """
    Test uninstalling an editable installation from svn.
    """
    result = script.pip(
        "install",
        "-e",
        "{checkout}#egg=initools".format(
            checkout=local_checkout("svn+http://svn.colorstudy.com/INITools", tmpdir)
        ),
    )
    result.assert_installed("INITools")
    result2 = script.pip("uninstall", "-y", "initools")
    assert script.venv / "src" / "initools" in result2.files_after
    assert_all_changes(
        result,
        result2,
        [
            script.venv / "src",
            script.venv / "build",
            script.site_packages / "easy-install.pth",
        ],
    )


@pytest.mark.network
def test_uninstall_editable_with_source_outside_venv(script, tmpdir):
    """
    Test uninstalling editable install from existing source outside the venv.
    """
    try:
        temp = mkdtemp()
        temp_pkg_dir = join(temp, "pip-test-package")
        _test_uninstall_editable_with_source_outside_venv(
            script,
            tmpdir,
            temp_pkg_dir,
        )
    finally:
        rmtree(temp)


def _test_uninstall_editable_with_source_outside_venv(
    script,
    tmpdir,
    temp_pkg_dir,
):
    result = script.run(
        "git",
        "clone",
        local_repo("git+git://github.com/pypa/pip-test-package", tmpdir),
        temp_pkg_dir,
        expect_stderr=True,
    )
    result2 = script.pip("install", "-e", temp_pkg_dir)
    result2.did_create(join(script.site_packages, "pip-test-package.egg-link"))
    result3 = script.pip("uninstall", "-y", "pip-test-package")
    assert_all_changes(
        result,
        result3,
        [script.venv / "build", script.site_packages / "easy-install.pth"],
    )


@pytest.mark.xfail
@pytest.mark.network
@need_svn
def test_uninstall_from_reqs_file(script, tmpdir):
    """
    Test uninstall from a requirements file.

    """
    local_svn_url = local_checkout(
        "svn+http://svn.colorstudy.com/INITools",
        tmpdir,
    )
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
            -e {url}#egg=initools
            # and something else to test out:
            PyLogo<0.4
        """
        ).format(url=local_svn_url)
    )
    result = script.pip("install", "-r", "test-req.txt")
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
            # -f, -i, and --extra-index-url should all be ignored by uninstall
            -f http://www.example.com
            -i http://www.example.com
            --extra-index-url http://www.example.com

            -e {url}#egg=initools
            # and something else to test out:
            PyLogo<0.4
        """
        ).format(url=local_svn_url)
    )
    result2 = script.pip("uninstall", "-r", "test-req.txt", "-y")
    assert_all_changes(
        result,
        result2,
        [
            script.venv / "build",
            script.venv / "src",
            script.scratch / "test-req.txt",
            script.site_packages / "easy-install.pth",
        ],
    )


def test_uninstallpathset_no_paths(caplog):
    """
    Test UninstallPathSet logs notification when there are no paths to
    uninstall
    """
    from pkg_resources import get_distribution

    from pip._internal.req.req_uninstall import UninstallPathSet

    caplog.set_level(logging.INFO)

    test_dist = get_distribution("pip")
    uninstall_set = UninstallPathSet(test_dist)
    uninstall_set.remove()  # with no files added to set

    assert "Can't uninstall 'pip'. No files were found to uninstall." in caplog.text


def test_uninstall_non_local_distutils(caplog, monkeypatch, tmpdir):
    einfo = tmpdir.joinpath("thing-1.0.egg-info")
    with open(einfo, "wb"):
        pass

    get_dist = Mock()
    get_dist.return_value = Mock(
        key="thing",
        project_name="thing",
        egg_info=einfo,
        location=einfo,
    )
    monkeypatch.setattr("pip._vendor.pkg_resources.get_distribution", get_dist)

    req = install_req_from_line("thing")
    req.uninstall()

    assert os.path.exists(einfo)


def test_uninstall_wheel(script, data):
    """
    Test uninstalling a wheel
    """
    package = data.packages.joinpath("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index")
    dist_info_folder = script.site_packages / "simple.dist-0.1.dist-info"
    result.did_create(dist_info_folder)
    result2 = script.pip("uninstall", "simple.dist", "-y")
    assert_all_changes(result, result2, [])


@pytest.mark.parametrize(
    "installer",
    [
        FileNotFoundError,
        IsADirectoryError,
        "",
        os.linesep,
        b"\xc0\xff\xee",
        "pip",
        "MegaCorp Cloud Install-O-Matic",
    ],
)
def test_uninstall_without_record_fails(script, data, installer):
    """
    Test uninstalling a package installed without RECORD
    """
    package = data.packages.joinpath("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index")
    dist_info_folder = script.site_packages / "simple.dist-0.1.dist-info"
    result.did_create(dist_info_folder)

    # Remove RECORD
    record_path = dist_info_folder / "RECORD"
    (script.base_path / record_path).unlink()
    ignore_changes = [record_path]

    # Populate, remove or otherwise break INSTALLER
    installer_path = dist_info_folder / "INSTALLER"
    ignore_changes += [installer_path]
    installer_path = script.base_path / installer_path
    if installer in (FileNotFoundError, IsADirectoryError):
        installer_path.unlink()
        if installer is IsADirectoryError:
            installer_path.mkdir()
    else:
        if isinstance(installer, bytes):
            installer_path.write_bytes(installer)
        else:
            installer_path.write_text(installer + os.linesep)

    result2 = script.pip("uninstall", "simple.dist", "-y", expect_error=True)
    expected_error_message = (
        "ERROR: Cannot uninstall simple.dist 0.1, RECORD file not found."
    )
    if not isinstance(installer, str) or not installer.strip() or installer == "pip":
        expected_error_message += (
            " You might be able to recover from this via: "
            "'pip install --force-reinstall --no-deps "
            "simple.dist==0.1'."
        )
    elif installer:
        expected_error_message += " Hint: The package was installed by {}.".format(
            installer
        )
    assert result2.stderr.rstrip() == expected_error_message
    assert_all_changes(result.files_after, result2, ignore_changes)


@pytest.mark.skipif("sys.platform == 'win32'")
def test_uninstall_with_symlink(script, data, tmpdir):
    """
    Test uninstalling a wheel, with an additional symlink
    https://github.com/pypa/pip/issues/6892
    """
    package = data.packages.joinpath("simple.dist-0.1-py2.py3-none-any.whl")
    script.pip("install", package, "--no-index")
    symlink_target = tmpdir / "target"
    symlink_target.mkdir()
    symlink_source = script.site_packages / "symlink"
    (script.base_path / symlink_source).symlink_to(symlink_target)
    st_mode = symlink_target.stat().st_mode
    distinfo_path = script.site_packages_path / "simple.dist-0.1.dist-info"
    record_path = distinfo_path / "RECORD"
    with open(record_path, "a") as f:
        f.write("symlink,,\n")
    uninstall_result = script.pip("uninstall", "simple.dist", "-y")
    assert symlink_source in uninstall_result.files_deleted
    assert symlink_target.stat().st_mode == st_mode


def test_uninstall_setuptools_develop_install(script, data):
    """Try uninstall after setup.py develop followed of setup.py install"""
    pkg_path = data.packages.joinpath("FSPkg")
    script.run("python", "setup.py", "develop", expect_stderr=True, cwd=pkg_path)
    script.run("python", "setup.py", "install", expect_stderr=True, cwd=pkg_path)
    script.assert_installed(FSPkg="0.1.dev0")
    # Uninstall both develop and install
    uninstall = script.pip("uninstall", "FSPkg", "-y")
    assert any(filename.endswith(".egg") for filename in uninstall.files_deleted.keys())
    uninstall2 = script.pip("uninstall", "FSPkg", "-y")
    assert (
        join(script.site_packages, "FSPkg.egg-link") in uninstall2.files_deleted
    ), list(uninstall2.files_deleted.keys())
    script.assert_not_installed("FSPkg")


def test_uninstall_editable_and_pip_install(script, data):
    """Try uninstall after pip install -e after pip install"""
    # SETUPTOOLS_SYS_PATH_TECHNIQUE=raw removes the assumption that `-e`
    # installs are always higher priority than regular installs.
    # This becomes the default behavior in setuptools 25.
    script.environ["SETUPTOOLS_SYS_PATH_TECHNIQUE"] = "raw"

    pkg_path = data.packages.joinpath("FSPkg")
    script.pip("install", "-e", ".", expect_stderr=True, cwd=pkg_path)
    # ensure both are installed with --ignore-installed:
    script.pip("install", "--ignore-installed", ".", expect_stderr=True, cwd=pkg_path)
    script.assert_installed(FSPkg="0.1.dev0")
    # Uninstall both develop and install
    uninstall = script.pip("uninstall", "FSPkg", "-y")
    assert not any(
        filename.endswith(".egg-link") for filename in uninstall.files_deleted.keys()
    )
    uninstall2 = script.pip("uninstall", "FSPkg", "-y")
    assert (
        join(script.site_packages, "FSPkg.egg-link") in uninstall2.files_deleted
    ), list(uninstall2.files_deleted.keys())
    script.assert_not_installed("FSPkg")


def test_uninstall_editable_and_pip_install_easy_install_remove(script, data):
    """Try uninstall after pip install -e after pip install
    and removing easy-install.pth"""
    # SETUPTOOLS_SYS_PATH_TECHNIQUE=raw removes the assumption that `-e`
    # installs are always higher priority than regular installs.
    # This becomes the default behavior in setuptools 25.
    script.environ["SETUPTOOLS_SYS_PATH_TECHNIQUE"] = "raw"

    # Rename easy-install.pth to pip-test.pth
    easy_install_pth = join(script.site_packages_path, "easy-install.pth")
    pip_test_pth = join(script.site_packages_path, "pip-test.pth")
    os.rename(easy_install_pth, pip_test_pth)

    # Install FSPkg
    pkg_path = data.packages.joinpath("FSPkg")
    script.pip("install", "-e", ".", expect_stderr=True, cwd=pkg_path)

    # Rename easy-install.pth to pip-test-fspkg.pth
    pip_test_fspkg_pth = join(script.site_packages_path, "pip-test-fspkg.pth")
    os.rename(easy_install_pth, pip_test_fspkg_pth)

    # Confirm that FSPkg is installed
    script.assert_installed(FSPkg="0.1.dev0")

    # Remove pip-test-fspkg.pth
    os.remove(pip_test_fspkg_pth)

    # Uninstall will fail with given warning
    uninstall = script.pip("uninstall", "FSPkg", "-y")
    assert "Cannot remove entries from nonexistent file" in uninstall.stderr

    assert (
        join(script.site_packages, "FSPkg.egg-link") in uninstall.files_deleted
    ), list(uninstall.files_deleted.keys())

    # Confirm that FSPkg is uninstalled
    script.assert_not_installed("FSPkg")

    # Rename pip-test.pth back to easy-install.pth
    os.rename(pip_test_pth, easy_install_pth)


def test_uninstall_ignores_missing_packages(script, data):
    """Uninstall of a non existent package prints a warning and exits cleanly"""
    result = script.pip(
        "uninstall",
        "-y",
        "non-existent-pkg",
        expect_stderr=True,
    )

    assert "Skipping non-existent-pkg as it is not installed." in result.stderr
    assert result.returncode == 0, "Expected clean exit"


def test_uninstall_ignores_missing_packages_and_uninstalls_rest(script, data):
    script.pip_install_local("simple")
    result = script.pip(
        "uninstall",
        "-y",
        "non-existent-pkg",
        "simple",
        expect_stderr=True,
    )

    assert "Skipping non-existent-pkg as it is not installed." in result.stderr
    assert "Successfully uninstalled simple" in result.stdout
    assert result.returncode == 0, "Expected clean exit"
