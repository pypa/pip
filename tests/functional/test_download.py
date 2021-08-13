import os.path
import shutil
import textwrap
from hashlib import sha256

import pytest

from pip._internal.cli.status_codes import ERROR
from pip._internal.utils.urls import path_to_url
from tests.lib import create_really_basic_wheel
from tests.lib.path import Path
from tests.lib.server import file_response


def fake_wheel(data, wheel_path):
    wheel_name = os.path.basename(wheel_path)
    name, version, rest = wheel_name.split("-", 2)
    wheel_data = create_really_basic_wheel(name, version)
    data.packages.joinpath(wheel_path).write_bytes(wheel_data)


@pytest.mark.network
def test_download_if_requested(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip("download", "-d", "pip_downloads", "INITools==0.1")
    result.did_create(Path("scratch") / "pip_downloads" / "INITools-0.1.tar.gz")
    result.did_not_create(script.site_packages / "initools")


@pytest.mark.network
def test_basic_download_setuptools(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip("download", "setuptools")
    setuptools_prefix = str(Path("scratch") / "setuptools")
    assert any(path.startswith(setuptools_prefix) for path in result.files_created)


def test_download_wheel(script, data):
    """
    Test using "pip download" to download a *.whl archive.
    """
    result = script.pip(
        "download", "--no-index", "-f", data.packages, "-d", ".", "meta"
    )
    result.did_create(Path("scratch") / "meta-1.0-py2.py3-none-any.whl")
    result.did_not_create(script.site_packages / "piptestpackage")


@pytest.mark.network
def test_single_download_from_requirements_file(script):
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
def test_basic_download_should_download_dependencies(script):
    """
    It should download dependencies (in the scratch path)
    """
    result = script.pip("download", "Paste[openid]==1.7.5.1", "-d", ".")
    result.did_create(Path("scratch") / "Paste-1.7.5.1.tar.gz")
    openid_tarball_prefix = str(Path("scratch") / "python-openid-")
    assert any(path.startswith(openid_tarball_prefix) for path in result.files_created)
    result.did_not_create(script.site_packages / "openid")


def test_download_wheel_archive(script, data):
    """
    It should download a wheel archive path
    """
    wheel_filename = "colander-0.9.9-py2.py3-none-any.whl"
    wheel_path = "/".join((data.find_links, wheel_filename))
    result = script.pip("download", wheel_path, "-d", ".", "--no-deps")
    result.did_create(Path("scratch") / wheel_filename)


def test_download_should_download_wheel_deps(script, data):
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
def test_download_should_skip_existing_files(script):
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
def test_download_vcs_link(script):
    """
    It should allow -d flag for vcs links, regression test for issue #798.
    """
    result = script.pip(
        "download", "-d", ".", "git+git://github.com/pypa/pip-test-package.git"
    )
    result.did_create(Path("scratch") / "pip-test-package-0.1.1.zip")
    result.did_not_create(script.site_packages / "piptestpackage")


def test_only_binary_set_then_download_specific_platform(script, data):
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


def test_no_deps_set_then_download_specific_platform(script, data):
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


def test_download_specific_platform_fails(script, data):
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


def test_no_binary_set_then_download_specific_platform_fails(script, data):
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


def test_download_specify_platform(script, data):
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
    def test_download_universal(self, platform, script, data):
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
        wheel_abi,
        platform,
        script,
        data,
    ):
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

    def test_explicit_platform_only(self, data, script):
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


def test_download__python_version(script, data):
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


def make_wheel_with_python_requires(script, package_name, python_requires):
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


def test_download__python_version_used_for_python_requires(
    script,
    data,
    with_wheel,
):
    """
    Test that --python-version is used for the Requires-Python check.
    """
    wheel_path = make_wheel_with_python_requires(
        script,
        "mypackage",
        python_requires="==3.2",
    )
    wheel_dir = os.path.dirname(wheel_path)

    def make_args(python_version):
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


def test_download_ignore_requires_python_dont_fail_with_wrong_python(
    script,
    with_wheel,
):
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


def test_download_specify_abi(script, data):
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


def test_download_specify_implementation(script, data):
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


def test_download_exit_status_code_when_no_requirements(script):
    """
    Test download exit status code when no requirements specified
    """
    result = script.pip("download", expect_error=True)
    assert "You must give at least one requirement to download" in result.stderr
    assert result.returncode == ERROR


def test_download_exit_status_code_when_blank_requirements_file(script):
    """
    Test download exit status code when blank requirements file specified
    """
    script.scratch_path.joinpath("blank.txt").write_text("\n")
    script.pip("download", "-r", "blank.txt")


def test_download_prefer_binary_when_tarball_higher_than_wheel(script, data):
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


def test_prefer_binary_tarball_higher_than_wheel_req_file(script, data):
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


def test_download_prefer_binary_when_wheel_doesnt_satisfy_req(script, data):
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


def test_prefer_binary_when_wheel_doesnt_satisfy_req_req_file(script, data):
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


def test_download_prefer_binary_when_only_tarball_exists(script, data):
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


def test_prefer_binary_when_only_tarball_exists_req_file(script, data):
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
def shared_script(tmpdir_factory, script_factory):
    tmpdir = Path(str(tmpdir_factory.mktemp("download_shared_script")))
    script = script_factory(tmpdir.joinpath("workspace"))
    return script


def test_download_file_url(shared_script, shared_data, tmpdir):
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


def test_download_file_url_existing_ok_download(shared_script, shared_data, tmpdir):
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


def test_download_file_url_existing_bad_download(shared_script, shared_data, tmpdir):
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


def test_download_http_url_bad_hash(shared_script, shared_data, tmpdir, mock_server):
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


def test_download_editable(script, data, tmpdir):
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
