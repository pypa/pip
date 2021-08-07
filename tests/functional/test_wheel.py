"""'pip wheel' tests"""
import os
import re
import sys
from os.path import exists

import pytest

from pip._internal.cli.status_codes import ERROR
from tests.lib import pyversion  # noqa: F401


@pytest.fixture(autouse=True)
def auto_with_wheel(with_wheel):
    pass


def add_files_to_dist_directory(folder):
    (folder / "dist").mkdir(parents=True)
    (folder / "dist" / "a_name-0.0.1.tar.gz").write_text("hello")
    # Not adding a wheel file since that confuses setuptools' backend.
    # (folder / 'dist' / 'a_name-0.0.1-py2.py3-none-any.whl').write_text(
    #     "hello"
    # )


def test_wheel_exit_status_code_when_no_requirements(script):
    """
    Test wheel exit status code when no requirements specified
    """
    result = script.pip("wheel", expect_error=True)
    assert "You must give at least one requirement to wheel" in result.stderr
    assert result.returncode == ERROR


def test_wheel_exit_status_code_when_blank_requirements_file(script):
    """
    Test wheel exit status code when blank requirements file specified
    """
    script.scratch_path.joinpath("blank.txt").write_text("\n")
    script.pip("wheel", "-r", "blank.txt")


def test_pip_wheel_success(script, data):
    """
    Test 'pip wheel' success.
    """
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "simple==3.0",
    )
    wheel_file_name = f"simple-3.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    assert re.search(
        r"Created wheel for simple: "
        r"filename={filename} size=\d+ sha256=[A-Fa-f0-9]{{64}}".format(
            filename=re.escape(wheel_file_name)
        ),
        result.stdout,
    )
    assert re.search(r"^\s+Stored in directory: ", result.stdout, re.M)
    result.did_create(wheel_file_path)
    assert "Successfully built simple" in result.stdout, result.stdout


def test_pip_wheel_build_cache(script, data):
    """
    Test 'pip wheel' builds and caches.
    """
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "simple==3.0",
    )
    wheel_file_name = f"simple-3.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
    assert "Successfully built simple" in result.stdout, result.stdout
    # remove target file
    (script.scratch_path / wheel_file_name).unlink()
    # pip wheel again and test that no build occurs since
    # we get the wheel from cache
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "simple==3.0",
    )
    result.did_create(wheel_file_path)
    assert "Successfully built simple" not in result.stdout, result.stdout


def test_basic_pip_wheel_downloads_wheels(script, data):
    """
    Test 'pip wheel' downloads wheels
    """
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "simple.dist",
    )
    wheel_file_name = "simple.dist-0.1-py2.py3-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
    assert "Saved" in result.stdout, result.stdout


def test_pip_wheel_build_relative_cachedir(script, data):
    """
    Test 'pip wheel' builds and caches with a non-absolute cache directory.
    """
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "--cache-dir",
        "./cache",
        "simple==3.0",
    )
    assert result.returncode == 0


def test_pip_wheel_builds_when_no_binary_set(script, data):
    data.packages.joinpath("simple-3.0-py2.py3-none-any.whl").touch()
    # Check that the wheel package is ignored
    res = script.pip(
        "wheel",
        "--no-index",
        "--no-binary",
        ":all:",
        "-f",
        data.find_links,
        "simple==3.0",
    )
    assert "Building wheel for simple" in str(res), str(res)


@pytest.mark.skipif("sys.platform == 'win32'")
def test_pip_wheel_readonly_cache(script, data, tmpdir):
    cache_dir = tmpdir / "cache"
    cache_dir.mkdir()
    os.chmod(cache_dir, 0o400)  # read-only cache
    # Check that the wheel package is ignored
    res = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "--cache-dir",
        cache_dir,
        "simple==3.0",
        allow_stderr_warning=True,
    )
    assert res.returncode == 0
    assert "The cache has been disabled." in str(res), str(res)


def test_pip_wheel_builds_editable_deps(script, data):
    """
    Test 'pip wheel' finds and builds dependencies of editables
    """
    editable_path = os.path.join(data.src, "requires_simple")
    result = script.pip(
        "wheel", "--no-index", "-f", data.find_links, "-e", editable_path
    )
    wheel_file_name = f"simple-1.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)


def test_pip_wheel_builds_editable(script, data):
    """
    Test 'pip wheel' builds an editable package
    """
    editable_path = os.path.join(data.src, "simplewheel-1.0")
    result = script.pip(
        "wheel", "--no-index", "-f", data.find_links, "-e", editable_path
    )
    wheel_file_name = f"simplewheel-1.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)


@pytest.mark.network
def test_pip_wheel_git_editable_keeps_clone(script, tmpdir):
    """
    Test that `pip wheel -e giturl` preserves a git clone in src.
    """
    script.pip(
        "wheel",
        "--no-deps",
        "-e",
        "git+https://github.com/pypa/pip-test-package#egg=pip-test-package",
        "--src",
        tmpdir / "src",
        "--wheel-dir",
        tmpdir,
    )
    assert (tmpdir / "src" / "pip-test-package").exists()
    assert (tmpdir / "src" / "pip-test-package" / ".git").exists()


def test_pip_wheel_builds_editable_does_not_create_zip(script, data, tmpdir):
    """
    Test 'pip wheel' of editables does not create zip files
    (regression test for issue #9122)
    """
    wheel_dir = tmpdir / "wheel_dir"
    wheel_dir.mkdir()
    editable_path = os.path.join(data.src, "simplewheel-1.0")
    script.pip("wheel", "--no-deps", "-e", editable_path, "-w", wheel_dir)
    wheels = os.listdir(wheel_dir)
    assert len(wheels) == 1
    assert wheels[0].endswith(".whl")


def test_pip_wheel_fail(script, data):
    """
    Test 'pip wheel' failure.
    """
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "wheelbroken==0.1",
        expect_error=True,
    )
    wheel_file_name = f"wheelbroken-0.1-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_not_create(wheel_file_path)
    assert "FakeError" in result.stderr, result.stderr
    assert "Failed to build wheelbroken" in result.stdout, result.stdout
    assert result.returncode != 0


@pytest.mark.xfail(reason="The --build option was removed")
def test_no_clean_option_blocks_cleaning_after_wheel(
    script,
    data,
    resolver_variant,
):
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    build = script.venv_path / "build"
    result = script.pip(
        "wheel",
        "--no-clean",
        "--no-index",
        "--build",
        build,
        f"--find-links={data.find_links}",
        "simple",
        expect_temp=True,
        # TODO: allow_stderr_warning is used for the --build deprecation,
        #       remove it when removing support for --build
        allow_stderr_warning=True,
    )

    if resolver_variant == "legacy":
        build = build / "simple"
        message = f"build/simple should still exist {result}"
        assert exists(build), message


def test_pip_wheel_source_deps(script, data):
    """
    Test 'pip wheel' finds and builds source archive dependencies
    of wheels
    """
    # 'requires_source' is a wheel that depends on the 'source' project
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "requires_source",
    )
    wheel_file_name = f"source-1.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
    assert "Successfully built source" in result.stdout, result.stdout


def test_wheel_package_with_latin1_setup(script, data):
    """Create a wheel from a package with latin-1 encoded setup.py."""

    pkg_to_wheel = data.packages.joinpath("SetupPyLatin1")
    result = script.pip("wheel", pkg_to_wheel)
    assert "Successfully built SetupPyUTF8" in result.stdout


def test_pip_wheel_with_pep518_build_reqs(script, data, common_wheels):
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "-f",
        common_wheels,
        "pep518==3.0",
    )
    wheel_file_name = f"pep518-3.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
    assert "Successfully built pep518" in result.stdout, result.stdout
    assert "Installing build dependencies" in result.stdout, result.stdout


def test_pip_wheel_with_pep518_build_reqs_no_isolation(script, data):
    script.pip_install_local("simplewheel==2.0")
    result = script.pip(
        "wheel",
        "--no-index",
        "-f",
        data.find_links,
        "--no-build-isolation",
        "pep518==3.0",
    )
    wheel_file_name = f"pep518-3.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
    assert "Successfully built pep518" in result.stdout, result.stdout
    assert "Installing build dependencies" not in result.stdout, result.stdout


def test_pip_wheel_with_user_set_in_config(script, data, common_wheels):
    config_file = script.scratch_path / "pip.conf"
    script.environ["PIP_CONFIG_FILE"] = str(config_file)
    config_file.write_text("[install]\nuser = true")
    result = script.pip(
        "wheel", data.src / "withpyproject", "--no-index", "-f", common_wheels
    )
    assert "Successfully built withpyproject" in result.stdout, result.stdout


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="The empty extension module does not work on Win",
)
def test_pip_wheel_ext_module_with_tmpdir_inside(script, data, common_wheels):
    tmpdir = data.src / "extension/tmp"
    tmpdir.mkdir()
    script.environ["TMPDIR"] = str(tmpdir)

    # To avoid a test dependency on a C compiler, we set the env vars to "noop"
    # The .c source is empty anyway
    script.environ["CC"] = script.environ["LDSHARED"] = "true"

    result = script.pip(
        "wheel", data.src / "extension", "--no-index", "-f", common_wheels
    )
    assert "Successfully built extension" in result.stdout, result.stdout


@pytest.mark.network
def test_pep517_wheels_are_not_confused_with_other_files(script, tmpdir, data):
    """Check correct wheels are copied. (#6196)"""
    pkg_to_wheel = data.src / "withpyproject"
    add_files_to_dist_directory(pkg_to_wheel)

    result = script.pip("wheel", pkg_to_wheel, "-w", script.scratch_path)
    assert "Installing build dependencies" in result.stdout, result.stdout

    wheel_file_name = f"withpyproject-0.0.1-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)


def test_legacy_wheels_are_not_confused_with_other_files(script, tmpdir, data):
    """Check correct wheels are copied. (#6196)"""
    pkg_to_wheel = data.src / "simplewheel-1.0"
    add_files_to_dist_directory(pkg_to_wheel)

    result = script.pip("wheel", pkg_to_wheel, "-w", script.scratch_path)
    assert "Installing build dependencies" not in result.stdout, result.stdout

    wheel_file_name = f"simplewheel-1.0-py{pyversion[0]}-none-any.whl"
    wheel_file_path = script.scratch / wheel_file_name
    result.did_create(wheel_file_path)
