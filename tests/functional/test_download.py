import json
import os.path
import shutil
import textwrap
import uuid
from hashlib import sha256
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest
from pip._vendor.packaging.requirements import Requirement

from pip._internal.cli.status_codes import ERROR
from pip._internal.models.direct_url import (
    ArchiveInfo,
    DirectUrl,
    DirInfo,
    InfoType,
    VcsInfo,
)
from pip._internal.utils.urls import path_to_url
from tests.conftest import MockServer, ScriptFactory
from tests.lib import PipTestEnvironment, TestData, create_really_basic_wheel
from tests.lib.path import Path
from tests.lib.server import file_response


def fake_wheel(data: TestData, wheel_path: str) -> None:
    wheel_name = os.path.basename(wheel_path)
    name, version, rest = wheel_name.split("-", 2)
    wheel_data = create_really_basic_wheel(name, version)
    data.packages.joinpath(wheel_path).write_bytes(wheel_data)


@pytest.mark.network
def test_download_if_requested(script: PipTestEnvironment) -> None:
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip("download", "-d", "pip_downloads", "INITools==0.1")
    result.did_create(Path("scratch") / "pip_downloads" / "INITools-0.1.tar.gz")
    result.did_not_create(script.site_packages / "initools")


@pytest.mark.network
def test_basic_download_setuptools(script: PipTestEnvironment) -> None:
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip("download", "setuptools")
    setuptools_prefix = str(Path("scratch") / "setuptools")
    assert any(path.startswith(setuptools_prefix) for path in result.files_created)


def test_download_wheel(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test using "pip download" to download a *.whl archive.
    """
    result = script.pip(
        "download", "--no-index", "-f", data.packages, "-d", ".", "meta"
    )
    result.did_create(Path("scratch") / "meta-1.0-py2.py3-none-any.whl")
    result.did_not_create(script.site_packages / "piptestpackage")


@pytest.mark.network
def test_single_download_from_requirements_file(script: PipTestEnvironment) -> None:
    """
    It should support download (in the scratch path) from PyPI from a
    requirements file
    """
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        INITools==0.1
        """
        )
    )
    result = script.pip(
        "download",
        "-r",
        script.scratch_path / "test-req.txt",
        "-d",
        ".",
    )
    result.did_create(Path("scratch") / "INITools-0.1.tar.gz")
    result.did_not_create(script.site_packages / "initools")


@pytest.mark.network
def test_basic_download_should_download_dependencies(
    script: PipTestEnvironment,
) -> None:
    """
    It should download dependencies (in the scratch path)
    """
    result = script.pip("download", "Paste[openid]==1.7.5.1", "-d", ".")
    result.did_create(Path("scratch") / "Paste-1.7.5.1.tar.gz")
    openid_tarball_prefix = str(Path("scratch") / "python-openid-")
    assert any(path.startswith(openid_tarball_prefix) for path in result.files_created)
    result.did_not_create(script.site_packages / "openid")


@pytest.mark.network
def test_dry_run_should_not_download_dependencies(
    script: PipTestEnvironment,
) -> None:
    """
    It should not download dependencies into the scratch path.
    """
    result = script.pip("download", "--dry-run", "Paste[openid]==1.7.5.1", "-d", ".")
    result.did_not_create(Path("scratch") / "Paste-1.7.5.1.tar.gz")


def test_download_wheel_archive(script: PipTestEnvironment, data: TestData) -> None:
    """
    It should download a wheel archive path
    """
    wheel_filename = "colander-0.9.9-py2.py3-none-any.whl"
    wheel_path = "/".join((data.find_links, wheel_filename))
    result = script.pip("download", wheel_path, "-d", ".", "--no-deps")
    result.did_create(Path("scratch") / wheel_filename)


def test_download_should_download_wheel_deps(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    It should download dependencies for wheels(in the scratch path)
    """
    wheel_filename = "colander-0.9.9-py2.py3-none-any.whl"
    dep_filename = "translationstring-1.1.tar.gz"
    wheel_path = "/".join((data.find_links, wheel_filename))
    result = script.pip(
        "download", wheel_path, "-d", ".", "--find-links", data.find_links, "--no-index"
    )
    result.did_create(Path("scratch") / wheel_filename)
    result.did_create(Path("scratch") / dep_filename)


@pytest.mark.network
def test_download_should_skip_existing_files(script: PipTestEnvironment) -> None:
    """
    It should not download files already existing in the scratch dir
    """
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        INITools==0.1
        """
        )
    )

    result = script.pip(
        "download",
        "-r",
        script.scratch_path / "test-req.txt",
        "-d",
        ".",
    )
    result.did_create(Path("scratch") / "INITools-0.1.tar.gz")
    result.did_not_create(script.site_packages / "initools")

    # adding second package to test-req.txt
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        INITools==0.1
        python-openid==2.2.5
        """
        )
    )

    # only the second package should be downloaded
    result = script.pip(
        "download",
        "-r",
        script.scratch_path / "test-req.txt",
        "-d",
        ".",
    )
    openid_tarball_prefix = str(Path("scratch") / "python-openid-")
    assert any(path.startswith(openid_tarball_prefix) for path in result.files_created)
    result.did_not_create(Path("scratch") / "INITools-0.1.tar.gz")
    result.did_not_create(script.site_packages / "initools")
    result.did_not_create(script.site_packages / "openid")


@pytest.mark.network
def test_download_vcs_link(script: PipTestEnvironment) -> None:
    """
    It should allow -d flag for vcs links, regression test for issue #798.
    """
    result = script.pip(
        "download", "-d", ".", "git+https://github.com/pypa/pip-test-package.git"
    )
    result.did_create(Path("scratch") / "pip-test-package-0.1.1.zip")
    result.did_not_create(script.site_packages / "piptestpackage")


def test_only_binary_set_then_download_specific_platform(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Confirm that specifying an interpreter/platform constraint
    is allowed when ``--only-binary=:all:`` is set.
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")


def test_no_deps_set_then_download_specific_platform(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Confirm that specifying an interpreter/platform constraint
    is allowed when ``--no-deps`` is set.
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--no-deps",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")


def test_download_specific_platform_fails(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Confirm that specifying an interpreter/platform constraint
    enforces that ``--no-deps`` or ``--only-binary=:all:`` is set.
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake",
        expect_error=True,
    )
    assert "--only-binary=:all:" in result.stderr


def test_no_binary_set_then_download_specific_platform_fails(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Confirm that specifying an interpreter/platform constraint
    enforces that ``--only-binary=:all:`` is set without ``--no-binary``.
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--no-binary=fake",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake",
        expect_error=True,
    )
    assert "--only-binary=:all:" in result.stderr


def test_download_specify_platform(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test using "pip download --platform" to download a .whl archive
    supported for a specific platform
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")

    # Confirm that universal wheels are returned even for specific
    # platforms.
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "macosx_10_9_x86_64",
        "fake",
    )

    data.reset()
    fake_wheel(data, "fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl")
    fake_wheel(data, "fake-2.0-py2.py3-none-linux_x86_64.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "macosx_10_10_x86_64",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl")

    # OSX platform wheels are not backward-compatible.
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "macosx_10_8_x86_64",
        "fake",
        expect_error=True,
    )

    # No linux wheel provided for this version.
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake==1",
        expect_error=True,
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "linux_x86_64",
        "fake==2",
    )
    result.did_create(Path("scratch") / "fake-2.0-py2.py3-none-linux_x86_64.whl")

    # Test with multiple supported platforms specified.
    data.reset()
    fake_wheel(data, "fake-3.0-py2.py3-none-linux_x86_64.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--platform",
        "manylinux1_x86_64",
        "--platform",
        "linux_x86_64",
        "--platform",
        "any",
        "fake==3",
    )
    result.did_create(Path("scratch") / "fake-3.0-py2.py3-none-linux_x86_64.whl")


class TestDownloadPlatformManylinuxes:
    """
    "pip download --platform" downloads a .whl archive supported for
    manylinux platforms.
    """

    @pytest.mark.parametrize(
        "platform",
        [
            "linux_x86_64",
            "manylinux1_x86_64",
            "manylinux2010_x86_64",
            "manylinux2014_x86_64",
        ],
    )
    def test_download_universal(
        self, platform: str, script: PipTestEnvironment, data: TestData
    ) -> None:
        """
        Universal wheels are returned even for specific platforms.
        """
        fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")
        result = script.pip(
            "download",
            "--no-index",
            "--find-links",
            data.find_links,
            "--only-binary=:all:",
            "--dest",
            ".",
            "--platform",
            platform,
            "fake",
        )
        result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")

    @pytest.mark.parametrize(
        "wheel_abi,platform",
        [
            ("manylinux1_x86_64", "manylinux1_x86_64"),
            ("manylinux1_x86_64", "manylinux2010_x86_64"),
            ("manylinux2010_x86_64", "manylinux2010_x86_64"),
            ("manylinux1_x86_64", "manylinux2014_x86_64"),
            ("manylinux2010_x86_64", "manylinux2014_x86_64"),
            ("manylinux2014_x86_64", "manylinux2014_x86_64"),
        ],
    )
    def test_download_compatible_manylinuxes(
        self,
        wheel_abi: str,
        platform: str,
        script: PipTestEnvironment,
        data: TestData,
    ) -> None:
        """
        Earlier manylinuxes are compatible with later manylinuxes.
        """
        wheel = f"fake-1.0-py2.py3-none-{wheel_abi}.whl"
        fake_wheel(data, wheel)
        result = script.pip(
            "download",
            "--no-index",
            "--find-links",
            data.find_links,
            "--only-binary=:all:",
            "--dest",
            ".",
            "--platform",
            platform,
            "fake",
        )
        result.did_create(Path("scratch") / wheel)

    def test_explicit_platform_only(
        self, data: TestData, script: PipTestEnvironment
    ) -> None:
        """
        When specifying the platform, manylinux1 needs to be the
        explicit platform--it won't ever be added to the compatible
        tags.
        """
        fake_wheel(data, "fake-1.0-py2.py3-none-linux_x86_64.whl")
        script.pip(
            "download",
            "--no-index",
            "--find-links",
            data.find_links,
            "--only-binary=:all:",
            "--dest",
            ".",
            "--platform",
            "linux_x86_64",
            "fake",
        )


def test_download__python_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test using "pip download --python-version" to download a .whl archive
    supported for a specific interpreter
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "2",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "3",
        "fake",
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "27",
        "fake",
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "33",
        "fake",
    )

    data.reset()
    fake_wheel(data, "fake-1.0-py2-none-any.whl")
    fake_wheel(data, "fake-2.0-py3-none-any.whl")

    # No py3 provided for version 1.
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "3",
        "fake==1.0",
        expect_error=True,
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "2",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "26",
        "fake",
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "3",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-2.0-py3-none-any.whl")


def make_wheel_with_python_requires(
    script: PipTestEnvironment, package_name: str, python_requires: str
) -> Path:
    """
    Create a wheel using the given python_requires.

    :return: the path to the wheel file.
    """
    package_dir = script.scratch_path / package_name
    package_dir.mkdir()

    text = textwrap.dedent(
        """\
    from setuptools import setup
    setup(name='{}',
          python_requires='{}',
          version='1.0')
    """
    ).format(package_name, python_requires)
    package_dir.joinpath("setup.py").write_text(text)
    script.run(
        "python",
        "setup.py",
        "bdist_wheel",
        "--universal",
        cwd=package_dir,
    )

    file_name = f"{package_name}-1.0-py2.py3-none-any.whl"
    return package_dir / "dist" / file_name


@pytest.mark.usefixtures("with_wheel")
def test_download__python_version_used_for_python_requires(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that --python-version is used for the Requires-Python check.
    """
    wheel_path = make_wheel_with_python_requires(
        script,
        "mypackage",
        python_requires="==3.2",
    )
    wheel_dir = os.path.dirname(wheel_path)

    def make_args(python_version: str) -> List[str]:
        return [
            "download",
            "--no-index",
            "--find-links",
            wheel_dir,
            "--only-binary=:all:",
            "--dest",
            ".",
            "--python-version",
            python_version,
            "mypackage==1.0",
        ]

    args = make_args("33")
    result = script.pip(*args, expect_error=True)
    expected_err = (
        "ERROR: Package 'mypackage' requires a different Python: "
        "3.3.0 not in '==3.2'"
    )
    assert expected_err in result.stderr, f"stderr: {result.stderr}"

    # Now try with a --python-version that satisfies the Requires-Python.
    args = make_args("32")
    script.pip(*args)  # no exception


@pytest.mark.usefixtures("with_wheel")
def test_download_ignore_requires_python_dont_fail_with_wrong_python(
    script: PipTestEnvironment,
) -> None:
    """
    Test that --ignore-requires-python ignores Requires-Python check.
    """
    wheel_path = make_wheel_with_python_requires(
        script,
        "mypackage",
        python_requires="==999",
    )
    wheel_dir = os.path.dirname(wheel_path)

    result = script.pip(
        "download",
        "--ignore-requires-python",
        "--no-index",
        "--find-links",
        wheel_dir,
        "--only-binary=:all:",
        "--dest",
        ".",
        "mypackage==1.0",
    )
    result.did_create(Path("scratch") / "mypackage-1.0-py2.py3-none-any.whl")


def test_download_specify_abi(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test using "pip download --abi" to download a .whl archive
    supported for a specific abi
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "--abi",
        "fake_abi",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "--abi",
        "none",
        "fake",
    )

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--abi",
        "cp27m",
        "fake",
    )

    data.reset()
    fake_wheel(data, "fake-1.0-fk2-fakeabi-fake_platform.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "2",
        "--implementation",
        "fk",
        "--platform",
        "fake_platform",
        "--abi",
        "fakeabi",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-fk2-fakeabi-fake_platform.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "--platform",
        "fake_platform",
        "--abi",
        "none",
        "fake",
        expect_error=True,
    )

    data.reset()
    fake_wheel(data, "fake-1.0-fk2-otherabi-fake_platform.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--python-version",
        "2",
        "--implementation",
        "fk",
        "--platform",
        "fake_platform",
        "--abi",
        "fakeabi",
        "--abi",
        "otherabi",
        "--abi",
        "none",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-fk2-otherabi-fake_platform.whl")


def test_download_specify_implementation(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test using "pip download --abi" to download a .whl archive
    supported for a specific abi
    """
    fake_wheel(data, "fake-1.0-py2.py3-none-any.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-py2.py3-none-any.whl")

    data.reset()
    fake_wheel(data, "fake-1.0-fk3-none-any.whl")
    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "--python-version",
        "3",
        "fake",
    )
    result.did_create(Path("scratch") / "fake-1.0-fk3-none-any.whl")

    result = script.pip(
        "download",
        "--no-index",
        "--find-links",
        data.find_links,
        "--only-binary=:all:",
        "--dest",
        ".",
        "--implementation",
        "fk",
        "--python-version",
        "2",
        "fake",
        expect_error=True,
    )


def test_download_exit_status_code_when_no_requirements(
    script: PipTestEnvironment,
) -> None:
    """
    Test download exit status code when no requirements specified
    """
    result = script.pip("download", expect_error=True)
    assert "You must give at least one requirement to download" in result.stderr
    assert result.returncode == ERROR


def test_download_exit_status_code_when_blank_requirements_file(
    script: PipTestEnvironment,
) -> None:
    """
    Test download exit status code when blank requirements file specified
    """
    script.scratch_path.joinpath("blank.txt").write_text("\n")
    script.pip("download", "-r", "blank.txt")


def test_download_prefer_binary_when_tarball_higher_than_wheel(
    script: PipTestEnvironment, data: TestData
) -> None:
    fake_wheel(data, "source-0.8-py2.py3-none-any.whl")
    result = script.pip(
        "download",
        "--prefer-binary",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
        "source",
    )
    result.did_create(Path("scratch") / "source-0.8-py2.py3-none-any.whl")
    result.did_not_create(Path("scratch") / "source-1.0.tar.gz")


def test_prefer_binary_tarball_higher_than_wheel_req_file(
    script: PipTestEnvironment, data: TestData
) -> None:
    fake_wheel(data, "source-0.8-py2.py3-none-any.whl")
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
                --prefer-binary
                 source
                """
        )
    )
    result = script.pip(
        "download",
        "-r",
        script.scratch_path / "test-req.txt",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
    )

    result.did_create(Path("scratch") / "source-0.8-py2.py3-none-any.whl")
    result.did_not_create(Path("scratch") / "source-1.0.tar.gz")


def test_download_prefer_binary_when_wheel_doesnt_satisfy_req(
    script: PipTestEnvironment, data: TestData
) -> None:
    fake_wheel(data, "source-0.8-py2.py3-none-any.whl")
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        source>0.9
        """
        )
    )

    result = script.pip(
        "download",
        "--prefer-binary",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
        "-r",
        script.scratch_path / "test-req.txt",
    )
    result.did_create(Path("scratch") / "source-1.0.tar.gz")
    result.did_not_create(Path("scratch") / "source-0.8-py2.py3-none-any.whl")


def test_prefer_binary_when_wheel_doesnt_satisfy_req_req_file(
    script: PipTestEnvironment, data: TestData
) -> None:
    fake_wheel(data, "source-0.8-py2.py3-none-any.whl")
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        --prefer-binary
        source>0.9
        """
        )
    )

    result = script.pip(
        "download",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
        "-r",
        script.scratch_path / "test-req.txt",
    )
    result.did_create(Path("scratch") / "source-1.0.tar.gz")
    result.did_not_create(Path("scratch") / "source-0.8-py2.py3-none-any.whl")


def test_download_prefer_binary_when_only_tarball_exists(
    script: PipTestEnvironment, data: TestData
) -> None:
    result = script.pip(
        "download",
        "--prefer-binary",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
        "source",
    )
    result.did_create(Path("scratch") / "source-1.0.tar.gz")


def test_prefer_binary_when_only_tarball_exists_req_file(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
            --prefer-binary
            source
            """
        )
    )
    result = script.pip(
        "download",
        "--no-index",
        "-f",
        data.packages,
        "-d",
        ".",
        "-r",
        script.scratch_path / "test-req.txt",
    )
    result.did_create(Path("scratch") / "source-1.0.tar.gz")


@pytest.fixture(scope="session")
def shared_script(
    tmpdir_factory: pytest.TempdirFactory, script_factory: ScriptFactory
) -> PipTestEnvironment:
    tmpdir = Path(str(tmpdir_factory.mktemp("download_shared_script")))
    script = script_factory(tmpdir.joinpath("workspace"))
    return script


def test_download_file_url(
    shared_script: PipTestEnvironment, shared_data: TestData, tmpdir: Path
) -> None:
    download_dir = tmpdir / "download"
    download_dir.mkdir()
    downloaded_path = download_dir / "simple-1.0.tar.gz"

    simple_pkg = shared_data.packages / "simple-1.0.tar.gz"

    shared_script.pip(
        "download",
        "-d",
        str(download_dir),
        "--no-index",
        path_to_url(str(simple_pkg)),
    )

    assert downloaded_path.exists()
    assert simple_pkg.read_bytes() == downloaded_path.read_bytes()


def test_download_file_url_existing_ok_download(
    shared_script: PipTestEnvironment, shared_data: TestData, tmpdir: Path
) -> None:
    download_dir = tmpdir / "download"
    download_dir.mkdir()
    downloaded_path = download_dir / "simple-1.0.tar.gz"
    fake_existing_package = shared_data.packages / "simple-2.0.tar.gz"
    shutil.copy(str(fake_existing_package), str(downloaded_path))
    downloaded_path_bytes = downloaded_path.read_bytes()
    digest = sha256(downloaded_path_bytes).hexdigest()

    simple_pkg = shared_data.packages / "simple-1.0.tar.gz"
    url = "{}#sha256={}".format(path_to_url(simple_pkg), digest)

    shared_script.pip("download", "-d", str(download_dir), url)

    assert downloaded_path_bytes == downloaded_path.read_bytes()


def test_download_file_url_existing_bad_download(
    shared_script: PipTestEnvironment, shared_data: TestData, tmpdir: Path
) -> None:
    download_dir = tmpdir / "download"
    download_dir.mkdir()
    downloaded_path = download_dir / "simple-1.0.tar.gz"
    fake_existing_package = shared_data.packages / "simple-2.0.tar.gz"
    shutil.copy(str(fake_existing_package), str(downloaded_path))

    simple_pkg = shared_data.packages / "simple-1.0.tar.gz"
    simple_pkg_bytes = simple_pkg.read_bytes()
    digest = sha256(simple_pkg_bytes).hexdigest()
    url = "{}#sha256={}".format(path_to_url(simple_pkg), digest)

    shared_script.pip("download", "-d", str(download_dir), url)

    assert simple_pkg_bytes == downloaded_path.read_bytes()


def test_download_http_url_bad_hash(
    shared_script: PipTestEnvironment,
    shared_data: TestData,
    tmpdir: Path,
    mock_server: MockServer,
) -> None:
    """
    If already-downloaded file has bad checksum, re-download.
    """
    download_dir = tmpdir / "download"
    download_dir.mkdir()
    downloaded_path = download_dir / "simple-1.0.tar.gz"
    fake_existing_package = shared_data.packages / "simple-2.0.tar.gz"
    shutil.copy(str(fake_existing_package), str(downloaded_path))

    simple_pkg = shared_data.packages / "simple-1.0.tar.gz"
    simple_pkg_bytes = simple_pkg.read_bytes()
    digest = sha256(simple_pkg_bytes).hexdigest()
    mock_server.set_responses([file_response(simple_pkg)])
    mock_server.start()
    base_address = f"http://{mock_server.host}:{mock_server.port}"
    url = f"{base_address}/simple-1.0.tar.gz#sha256={digest}"

    shared_script.pip("download", "-d", str(download_dir), url)

    assert simple_pkg_bytes == downloaded_path.read_bytes()

    mock_server.stop()
    requests = mock_server.get_requests()
    assert len(requests) == 1
    assert requests[0]["PATH_INFO"] == "/simple-1.0.tar.gz"
    assert requests[0]["HTTP_ACCEPT_ENCODING"] == "identity"


def test_download_editable(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """
    Test 'pip download' of editables in requirement file.
    """
    editable_path = str(data.src / "simplewheel-1.0").replace(os.path.sep, "/")
    requirements_path = tmpdir / "requirements.txt"
    requirements_path.write_text("-e " + editable_path + "\n")
    download_dir = tmpdir / "download_dir"
    script.pip(
        "download", "--no-deps", "-r", str(requirements_path), "-d", str(download_dir)
    )
    downloads = os.listdir(download_dir)
    assert len(downloads) == 1
    assert downloads[0].endswith(".zip")


@pytest.fixture(scope="function")
def json_report(
    shared_script: PipTestEnvironment, tmpdir: Path
) -> Callable[..., Dict[str, Any]]:
    """Execute `pip download --report` and parse the JSON file it writes out."""
    download_dir = tmpdir / "report"
    download_dir.mkdir()
    downloaded_path = download_dir / "report.json"

    def execute_pip_for_report_json(*args: str) -> Dict[str, Any]:
        shared_script.pip(
            "download",
            "--dry-run",
            f"--report={downloaded_path}",
            *args,
        )

        assert downloaded_path.exists()

        with open(downloaded_path, "r") as f:
            report = json.load(f)

        return report

    return execute_pip_for_report_json


@pytest.mark.network
@pytest.mark.parametrize(
    "package_name, package_filename, requirement, url_no_fragment, info",
    [
        ("simple", "simple-1.0.tar.gz", "simple==1.0", None, ArchiveInfo(hash=None)),
        (
            "simplewheel",
            "simplewheel-1.0-py2.py3-none-any.whl",
            "simplewheel==1.0",
            None,
            ArchiveInfo(hash=None),
        ),
        (
            "pip-test-package",
            "git+https://github.com/pypa/pip-test-package.git",
            "pip-test-package==0.1.1",
            "https://github.com/pypa/pip-test-package.git",
            VcsInfo(vcs="git", commit_id="5547fa909e83df8bd743d3978d6667497983a4b7"),
        ),
        ("symlinks", "symlinks", "symlinks==0.1.dev0", None, DirInfo(editable=False)),
        (
            "pex",
            "https://files.pythonhosted.org/packages/6f/7f/6b1e56fc291df523a02769ebe9b432f63f294475012c2c1f76d4cbb5321f/pex-2.1.61-py2.py3-none-any.whl#sha256=c09fda0f0477f3894f7a7a464b7e4c03d44734de46caddd25291565eed32a882",  # noqa: E501
            "pex==2.1.61",
            "https://files.pythonhosted.org/packages/6f/7f/6b1e56fc291df523a02769ebe9b432f63f294475012c2c1f76d4cbb5321f/pex-2.1.61-py2.py3-none-any.whl",  # noqa: E501
            ArchiveInfo(
                hash="sha256=c09fda0f0477f3894f7a7a464b7e4c03d44734de46caddd25291565eed32a882"  # noqa: E501
            ),
        ),
    ],
)
def test_download_report_direct_url_top_level(
    json_report: Callable[..., Dict[str, Any]],
    shared_data: TestData,
    package_name: str,
    package_filename: str,
    requirement: str,
    url_no_fragment: Optional[str],
    info: InfoType,
) -> None:
    """Test `pip download --report`'s "download_info" JSON field."""
    # If we are not referring to an explicit URL in our test parameterization, assume we
    # are referring to one of our test packages.
    if "://" in package_filename:
        simple_pkg = package_filename
    else:
        simple_pkg = path_to_url(str(shared_data.packages / package_filename))

    report = json_report("--no-index", simple_pkg)

    assert len(report["input_requirements"]) == 1
    # Wheel file paths provided as inputs will be converted into an equivalent
    # Requirement string 'a==x.y@scheme://path/to/wheel' instead of just the wheel path.
    assert report["input_requirements"][0].endswith(simple_pkg)

    candidate = report["candidates"][package_name]
    assert requirement == candidate["requirement"]
    direct_url = DirectUrl.from_dict(candidate["download_info"]["direct_url"])
    assert direct_url == DirectUrl(
        url_no_fragment or simple_pkg,
        info=info,
    )


@pytest.mark.network
def test_download_report_dependencies(
    json_report: Callable[..., Dict[str, Any]],
) -> None:
    """Test the result of a pinned resolve against PyPI."""
    report = json_report("cryptography==36.0.1", "cffi==1.15.0", "pycparser==2.21")
    assert sorted(report["input_requirements"]) == [
        "cffi==1.15.0",
        "cryptography==36.0.1",
        "pycparser==2.21",
    ]

    cryptography = report["candidates"]["cryptography"]
    assert cryptography["requirement"] == "cryptography==36.0.1"
    assert cryptography["requires_python"] == ">=3.6"
    assert cryptography["dependencies"] == {"cffi": "cffi>=1.12"}

    cffi = report["candidates"]["cffi"]
    assert cffi["requirement"] == "cffi==1.15.0"
    assert cffi["requires_python"] is None
    assert cffi["dependencies"] == {"pycparser": "pycparser"}

    pycparser = report["candidates"]["pycparser"]
    assert pycparser["requirement"] == "pycparser==2.21"
    assert pycparser["dependencies"] == {}
    assert pycparser["requires_python"] == "!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,>=2.7"


@pytest.mark.network
@pytest.mark.parametrize(
    "python_version",
    [
        "3.10.0",
        "3.10.1",
        "3.7.0",
        "3.8.0",
        "3.9.0",
    ],
)
def test_download_report_python_version(
    json_report: Callable[..., Dict[str, Any]],
    python_version: str,
) -> None:
    """Ensure the --python-version variable is respected in the --report JSON output."""
    report = json_report(
        f"--python-version={python_version}", "--only-binary=:all:", "wheel"
    )
    assert report["python_version"] == f"=={python_version}"


@pytest.fixture(scope="function")
def index_html_content(tmpdir: Path) -> Callable[..., Path]:
    """Generate a PyPI package index.html within a temporary local directory."""
    html_dir = tmpdir / "index_html_content"
    html_dir.mkdir()

    def generate_index_html_subdir(index_html: str) -> Path:
        """Create a new subdirectory after a UUID and write an index.html."""
        new_subdir = html_dir / uuid.uuid4().hex
        new_subdir.mkdir()

        with open(new_subdir / "index.html", "w") as f:
            f.write(index_html)

        return new_subdir

    return generate_index_html_subdir


@pytest.fixture(scope="function")
def json_report_for_index_content(
    shared_data: TestData,
    index_html_content: Callable[..., Path],
    json_report: Callable[..., Dict[str, Any]],
) -> Callable[..., Dict[str, Any]]:
    """Generate a PyPI package index within a local directory pointing to test data."""

    def generate_index_and_report_for_some_packages(
        packages: Dict[str, List[Tuple[str, str]]], *args: str
    ) -> Dict[str, Any]:
        """
        Produce a PyPI directory structure pointing to a subset of packages in
        test data, then execute `pip download --report ... -i ...` pointing to our
        generated index.
        """
        # (1) Generate the content for a PyPI index.html.
        pkg_links = "\n".join(
            f'    <a href="{pkg}/index.html">{pkg}</a>' for pkg in packages.keys()
        )
        index_html = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Simple index</title>
  </head>
  <body>
{pkg_links}
  </body>
</html>"""
        # (2) Generate the index.html in a new subdirectory of the temp directory.
        index_html_subdir = index_html_content(index_html)

        # (3) Generate subdirectories for individual packages, each with their own
        # index.html.
        for pkg, links in packages.items():
            pkg_subdir = index_html_subdir / pkg
            pkg_subdir.mkdir()

            download_links: List[str] = []
            for relative_path, additional_tag in links:
                # For each link to be added to the generated index.html for this
                # package, copy over the corresponding file in `shared_data.packages`.
                download_links.append(
                    f'    <a href="{relative_path}" {additional_tag}>{relative_path}</a><br/>'  # noqa: E501
                )
                shutil.copy(
                    shared_data.packages / relative_path, pkg_subdir / relative_path
                )

            # After collating all the download links and copying over the files, write
            # an index.html with the generated download links for each copied file.
            download_links_str = "\n".join(download_links)
            pkg_index_content = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for {pkg}</title>
  </head>
  <body>
    <h1>Links for {pkg}</h1>
{download_links_str}
  </body>
</html>"""
            with open(pkg_subdir / "index.html", "w") as f:
                f.write(pkg_index_content)

        return json_report("-i", path_to_url(index_html_subdir), *args)

    return generate_index_and_report_for_some_packages


_simple_packages: Dict[str, List[Tuple[str, str]]] = {
    "simple": [
        ("simple-1.0.tar.gz", ""),
        ("simple-2.0.tar.gz", 'data-dist-info-metadata="true"'),
        ("simple-3.0.tar.gz", 'data-dist-info-metadata="sha256=aabe42af"'),
    ]
}


@pytest.mark.parametrize(
    "requirement_to_download, dist_info_metadata",
    [
        (
            "simple==1.0",
            None,
        ),
        (
            "simple==2.0",
            ArchiveInfo(hash=None),
        ),
        (
            "simple==3.0",
            ArchiveInfo(hash="sha256=aabe42af"),
        ),
    ],
)
def test_download_report_dist_info_metadata(
    json_report_for_index_content: Callable[..., Dict[str, Any]],
    requirement_to_download: str,
    dist_info_metadata: Optional[ArchiveInfo],
) -> None:
    """Ensure `pip download --report` reflects PEP 658 metadata."""
    report = json_report_for_index_content(
        _simple_packages,
        requirement_to_download,
    )
    project_name = Requirement(requirement_to_download).name
    direct_url_json = report["candidates"][project_name]["download_info"][
        "dist_info_metadata"
    ]
    if dist_info_metadata is None:
        assert direct_url_json is None
    else:
        direct_url = DirectUrl.from_dict(direct_url_json)
        assert direct_url.info == dist_info_metadata
