import csv
import distutils
import glob
import os
import shutil

import pytest

from tests.lib import create_basic_wheel_for_package
from tests.lib.path import Path
from tests.lib.wheel import make_wheel


# assert_installed expects a package subdirectory, so give it to them
def make_wheel_with_file(name, version, **kwargs):
    extra_files = kwargs.setdefault("extra_files", {})
    extra_files[f"{name}/__init__.py"] = "# example"
    return make_wheel(name=name, version=version, **kwargs)


def test_install_from_future_wheel_version(script, tmpdir):
    """
    Test installing a wheel with a WHEEL metadata version that is:
    - a major version ahead of what we expect (not ok), and
    - a minor version ahead of what we expect (ok)
    """
    from tests.lib import TestFailure

    package = make_wheel_with_file(
        name="futurewheel",
        version="3.0",
        wheel_metadata_updates={"Wheel-Version": "3.0"},
    ).save_to_dir(tmpdir)

    result = script.pip("install", package, "--no-index", expect_error=True)
    with pytest.raises(TestFailure):
        result.assert_installed("futurewheel", without_egg_link=True, editable=False)

    package = make_wheel_with_file(
        name="futurewheel",
        version="1.9",
        wheel_metadata_updates={"Wheel-Version": "1.9"},
    ).save_to_dir(tmpdir)
    result = script.pip("install", package, "--no-index", expect_stderr=True)
    result.assert_installed("futurewheel", without_egg_link=True, editable=False)


def test_install_from_broken_wheel(script, data):
    """
    Test that installing a broken wheel fails properly
    """
    from tests.lib import TestFailure

    package = data.packages.joinpath("brokenwheel-1.0-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index", expect_error=True)
    with pytest.raises(TestFailure):
        result.assert_installed("futurewheel", without_egg_link=True, editable=False)


def test_basic_install_from_wheel(script, shared_data, tmpdir):
    """
    Test installing from a wheel (that has a script)
    """
    shutil.copy(shared_data.packages / "has.script-1.0-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "has.script==1.0",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    dist_info_folder = script.site_packages / "has.script-1.0.dist-info"
    result.did_create(dist_info_folder)
    script_file = script.bin / "script.py"
    result.did_create(script_file)


def test_basic_install_from_wheel_with_extras(script, shared_data, tmpdir):
    """
    Test installing from a wheel with extras.
    """
    shutil.copy(shared_data.packages / "complex_dist-0.1-py2.py3-none-any.whl", tmpdir)
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "complex-dist[simple]",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    dist_info_folder = script.site_packages / "complex_dist-0.1.dist-info"
    result.did_create(dist_info_folder)
    dist_info_folder = script.site_packages / "simple.dist-0.1.dist-info"
    result.did_create(dist_info_folder)


def test_basic_install_from_wheel_file(script, data):
    """
    Test installing directly from a wheel file.
    """
    package = data.packages.joinpath("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index")
    dist_info_folder = script.site_packages / "simple.dist-0.1.dist-info"
    result.did_create(dist_info_folder)
    installer = dist_info_folder / "INSTALLER"
    result.did_create(installer)
    with open(script.base_path / installer, "rb") as installer_file:
        installer_details = installer_file.read()
        assert installer_details == b"pip\n"
    installer_temp = dist_info_folder / "INSTALLER.pip"
    result.did_not_create(installer_temp)


# Installation seems to work, but scripttest fails to check.
# I really don't care now since we're desupporting it soon anyway.
def test_basic_install_from_unicode_wheel(script, data):
    """
    Test installing from a wheel (that has a script)
    """
    make_wheel(
        "unicode_package",
        "1.0",
        extra_files={
            "வணக்கம்/__init__.py": b"",
            "வணக்கம்/નમસ્તે.py": b"",
        },
    ).save_to_dir(script.scratch_path)

    result = script.pip(
        "install",
        "unicode_package==1.0",
        "--no-index",
        "--find-links",
        script.scratch_path,
    )
    dist_info_folder = script.site_packages / "unicode_package-1.0.dist-info"
    result.did_create(dist_info_folder)

    file1 = script.site_packages.joinpath("வணக்கம்", "__init__.py")
    result.did_create(file1)

    file2 = script.site_packages.joinpath("வணக்கம்", "નમસ્તે.py")
    result.did_create(file2)


def get_header_scheme_path_for_script(script, dist_name):
    command = (
        "from pip._internal.locations import get_scheme;"
        "scheme = get_scheme({!r});"
        "print(scheme.headers);"
    ).format(dist_name)
    result = script.run("python", "-c", command).stdout
    return Path(result.strip())


def test_install_from_wheel_with_headers(script):
    """
    Test installing from a wheel file with headers
    """
    header_text = "/* hello world */\n"
    package = make_wheel(
        "headers.dist",
        "0.1",
        extra_data_files={"headers/header.h": header_text},
    ).save_to_dir(script.scratch_path)
    result = script.pip("install", package, "--no-index")
    dist_info_folder = script.site_packages / "headers.dist-0.1.dist-info"
    result.did_create(dist_info_folder)

    header_scheme_path = get_header_scheme_path_for_script(script, "headers.dist")
    header_path = header_scheme_path / "header.h"
    assert header_path.read_text() == header_text


def test_install_wheel_with_target(script, shared_data, with_wheel, tmpdir):
    """
    Test installing a wheel using pip install --target
    """
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    target_dir = script.scratch_path / "target"
    result = script.pip(
        "install",
        "simple.dist==0.1",
        "-t",
        target_dir,
        "--no-index",
        "--find-links",
        tmpdir,
    )
    result.did_create(Path("scratch") / "target" / "simpledist")


def test_install_wheel_with_target_and_data_files(script, data, with_wheel):
    """
    Test for issue #4092. It will be checked that a data_files specification in
    setup.py is handled correctly when a wheel is installed with the --target
    option.

    The setup() for the wheel 'prjwithdatafile-1.0-py2.py3-none-any.whl' is as
    follows ::

        setup(
            name='prjwithdatafile',
            version='1.0',
            packages=['prjwithdatafile'],
            data_files=[
                (r'packages1', ['prjwithdatafile/README.txt']),
                (r'packages2', ['prjwithdatafile/README.txt'])
            ]
        )
    """
    target_dir = script.scratch_path / "prjwithdatafile"
    package = data.packages.joinpath("prjwithdatafile-1.0-py2.py3-none-any.whl")
    result = script.pip("install", package, "-t", target_dir, "--no-index")
    project_path = Path("scratch") / "prjwithdatafile"
    result.did_create(project_path / "packages1" / "README.txt")
    result.did_create(project_path / "packages2" / "README.txt")
    result.did_not_create(project_path / "lib" / "python")


def test_install_wheel_with_root(script, shared_data, tmpdir):
    """
    Test installing a wheel using pip install --root
    """
    root_dir = script.scratch_path / "root"
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "simple.dist==0.1",
        "--root",
        root_dir,
        "--no-index",
        "--find-links",
        tmpdir,
    )
    result.did_create(Path("scratch") / "root")


def test_install_wheel_with_prefix(script, shared_data, tmpdir):
    """
    Test installing a wheel using pip install --prefix
    """
    prefix_dir = script.scratch_path / "prefix"
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "simple.dist==0.1",
        "--prefix",
        prefix_dir,
        "--no-index",
        "--find-links",
        tmpdir,
    )
    lib = distutils.sysconfig.get_python_lib(prefix=Path("scratch") / "prefix")
    result.did_create(lib)


def test_install_from_wheel_installs_deps(script, data, tmpdir):
    """
    Test can install dependencies of wheels
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.joinpath("requires_source-1.0-py2.py3-none-any.whl")
    shutil.copy(data.packages / "source-1.0.tar.gz", tmpdir)
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        tmpdir,
        package,
    )
    result.assert_installed("source", editable=False)


def test_install_from_wheel_no_deps(script, data, tmpdir):
    """
    Test --no-deps works with wheel installs
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.joinpath("requires_source-1.0-py2.py3-none-any.whl")
    shutil.copy(data.packages / "source-1.0.tar.gz", tmpdir)
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        tmpdir,
        "--no-deps",
        package,
    )
    pkg_folder = script.site_packages / "source"
    result.did_not_create(pkg_folder)


def test_wheel_record_lines_in_deterministic_order(script, data):
    to_install = data.packages.joinpath("simplewheel-1.0-py2.py3-none-any.whl")
    result = script.pip("install", to_install)

    dist_info_folder = script.site_packages / "simplewheel-1.0.dist-info"
    record_path = dist_info_folder / "RECORD"

    result.did_create(dist_info_folder)
    result.did_create(record_path)

    record_path = result.files_created[record_path].full
    record_lines = [p for p in Path(record_path).read_text().split("\n") if p]
    assert record_lines == sorted(record_lines)


def test_wheel_record_lines_have_hash_for_data_files(script):
    package = make_wheel(
        "simple",
        "0.1.0",
        extra_data_files={
            "purelib/info.txt": "c",
        },
    ).save_to_dir(script.scratch_path)
    script.pip("install", package)
    record_file = script.site_packages_path / "simple-0.1.0.dist-info" / "RECORD"
    record_text = record_file.read_text()
    record_rows = list(csv.reader(record_text.splitlines()))
    records = {r[0]: r[1:] for r in record_rows}
    assert records["info.txt"] == [
        "sha256=Ln0sA6lQeuJl7PW1NWiFpTOTogKdJBOUmXJloaJa78Y",
        "1",
    ]


@pytest.mark.incompatible_with_test_venv
def test_install_user_wheel(script, shared_data, with_wheel, tmpdir):
    """
    Test user install from wheel (that has a script)
    """
    shutil.copy(shared_data.packages / "has.script-1.0-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "has.script==1.0",
        "--user",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    dist_info_folder = script.user_site / "has.script-1.0.dist-info"
    result.did_create(dist_info_folder)
    script_file = script.user_bin / "script.py"
    result.did_create(script_file)


def test_install_from_wheel_gen_entrypoint(script, shared_data, tmpdir):
    """
    Test installing scripts (entry points are generated)
    """
    shutil.copy(
        shared_data.packages / "script.wheel1a-0.1-py2.py3-none-any.whl",
        tmpdir,
    )
    result = script.pip(
        "install",
        "script.wheel1a==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    if os.name == "nt":
        wrapper_file = script.bin / "t1.exe"
    else:
        wrapper_file = script.bin / "t1"
    result.did_create(wrapper_file)

    if os.name != "nt":
        assert bool(os.access(script.base_path / wrapper_file, os.X_OK))


def test_install_from_wheel_gen_uppercase_entrypoint(script, shared_data, tmpdir):
    """
    Test installing scripts with uppercase letters in entry point names
    """
    shutil.copy(
        shared_data.packages / "console_scripts_uppercase-1.0-py2.py3-none-any.whl",
        tmpdir,
    )
    result = script.pip(
        "install",
        "console-scripts-uppercase==1.0",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    if os.name == "nt":
        # Case probably doesn't make any difference on NT
        wrapper_file = script.bin / "cmdName.exe"
    else:
        wrapper_file = script.bin / "cmdName"
    result.did_create(wrapper_file)

    if os.name != "nt":
        assert bool(os.access(script.base_path / wrapper_file, os.X_OK))


def test_install_from_wheel_gen_unicode_entrypoint(script):
    make_wheel(
        "script_wheel_unicode",
        "1.0",
        console_scripts=["進入點 = 模組:函式"],
    ).save_to_dir(script.scratch_path)

    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "script_wheel_unicode",
    )
    if os.name == "nt":
        result.did_create(script.bin.joinpath("進入點.exe"))
    else:
        result.did_create(script.bin.joinpath("進入點"))


def test_install_from_wheel_with_legacy(script, shared_data, tmpdir):
    """
    Test installing scripts (legacy scripts are preserved)
    """
    shutil.copy(
        shared_data.packages / "script.wheel2a-0.1-py2.py3-none-any.whl",
        tmpdir,
    )
    result = script.pip(
        "install",
        "script.wheel2a==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )

    legacy_file1 = script.bin / "testscript1.bat"
    legacy_file2 = script.bin / "testscript2"

    result.did_create(legacy_file1)
    result.did_create(legacy_file2)


def test_install_from_wheel_no_setuptools_entrypoint(script, shared_data, tmpdir):
    """
    Test that when we generate scripts, any existing setuptools wrappers in
    the wheel are skipped.
    """
    shutil.copy(shared_data.packages / "script.wheel1-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "script.wheel1==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    if os.name == "nt":
        wrapper_file = script.bin / "t1.exe"
    else:
        wrapper_file = script.bin / "t1"
    wrapper_helper = script.bin / "t1-script.py"

    # The wheel has t1.exe and t1-script.py. We will be generating t1 or
    # t1.exe depending on the platform. So we check that the correct wrapper
    # is present and that the -script.py helper has been skipped. We can't
    # easily test that the wrapper from the wheel has been skipped /
    # overwritten without getting very platform-dependent, so omit that.
    result.did_create(wrapper_file)
    result.did_not_create(wrapper_helper)


def test_skipping_setuptools_doesnt_skip_legacy(script, shared_data, tmpdir):
    """
    Test installing scripts (legacy scripts are preserved even when we skip
    setuptools wrappers)
    """
    shutil.copy(shared_data.packages / "script.wheel2-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "script.wheel2==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )

    legacy_file1 = script.bin / "testscript1.bat"
    legacy_file2 = script.bin / "testscript2"
    wrapper_helper = script.bin / "t1-script.py"

    result.did_create(legacy_file1)
    result.did_create(legacy_file2)
    result.did_not_create(wrapper_helper)


def test_install_from_wheel_gui_entrypoint(script, shared_data, tmpdir):
    """
    Test installing scripts (gui entry points are generated)
    """
    shutil.copy(shared_data.packages / "script.wheel3-0.1-py2.py3-none-any.whl", tmpdir)
    result = script.pip(
        "install",
        "script.wheel3==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    if os.name == "nt":
        wrapper_file = script.bin / "t1.exe"
    else:
        wrapper_file = script.bin / "t1"
    result.did_create(wrapper_file)


def test_wheel_compiles_pyc(script, shared_data, tmpdir):
    """
    Test installing from wheel with --compile on
    """
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    script.pip(
        "install",
        "--compile",
        "simple.dist==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "simpledist/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "simpledist/__pycache__/__init__*.pyc"
    )

    assert any(exists)


def test_wheel_no_compiles_pyc(script, shared_data, tmpdir):
    """
    Test installing from wheel with --compile on
    """
    shutil.copy(shared_data.packages / "simple.dist-0.1-py2.py3-none-any.whl", tmpdir)
    script.pip(
        "install",
        "--no-compile",
        "simple.dist==0.1",
        "--no-index",
        "--find-links",
        tmpdir,
    )
    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "simpledist/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "simpledist/__pycache__/__init__*.pyc"
    )

    assert not any(exists)


def test_install_from_wheel_uninstalls_old_version(script, data):
    # regression test for https://github.com/pypa/pip/issues/1825
    package = data.packages.joinpath("simplewheel-1.0-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index")
    package = data.packages.joinpath("simplewheel-2.0-py2.py3-none-any.whl")
    result = script.pip("install", package, "--no-index")
    dist_info_folder = script.site_packages / "simplewheel-2.0.dist-info"
    result.did_create(dist_info_folder)
    dist_info_folder = script.site_packages / "simplewheel-1.0.dist-info"
    result.did_not_create(dist_info_folder)


def test_wheel_compile_syntax_error(script, data):
    package = data.packages.joinpath("compilewheel-1.0-py2.py3-none-any.whl")
    result = script.pip("install", "--compile", package, "--no-index")
    assert "yield from" not in result.stdout
    assert "SyntaxError: " not in result.stdout


def test_wheel_install_with_no_cache_dir(script, tmpdir, data):
    """Check wheel installations work, even with no cache."""
    package = data.packages.joinpath("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip("install", "--no-cache-dir", "--no-index", package)
    result.assert_installed("simpledist", editable=False)


def test_wheel_install_fails_with_extra_dist_info(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
        extra_files={
            "unrelated-2.0.0.dist-info/WHEEL": "Wheel-Version: 1.0",
            "unrelated-2.0.0.dist-info/METADATA": ("Name: unrelated\nVersion: 2.0.0\n"),
        },
    )
    result = script.pip(
        "install", "--no-cache-dir", "--no-index", package, expect_error=True
    )
    assert "multiple .dist-info directories" in result.stderr


def test_wheel_install_fails_with_unrelated_dist_info(script):
    package = create_basic_wheel_for_package(script, "simple", "0.1.0")
    new_name = "unrelated-2.0.0-py2.py3-none-any.whl"
    new_package = os.path.join(os.path.dirname(package), new_name)
    shutil.move(package, new_package)

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        new_package,
        expect_error=True,
    )

    assert "'simple-0.1.0.dist-info' does not start with 'unrelated'" in result.stderr


def test_wheel_installs_ok_with_nested_dist_info(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
        extra_files={
            "subdir/unrelated-2.0.0.dist-info/WHEEL": "Wheel-Version: 1.0",
            "subdir/unrelated-2.0.0.dist-info/METADATA": (
                "Name: unrelated\nVersion: 2.0.0\n"
            ),
        },
    )
    script.pip("install", "--no-cache-dir", "--no-index", package)


def test_wheel_installs_ok_with_badly_encoded_irrelevant_dist_info_file(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
        extra_files={"simple-0.1.0.dist-info/AUTHORS.txt": b"\xff"},
    )
    script.pip("install", "--no-cache-dir", "--no-index", package)


def test_wheel_install_fails_with_badly_encoded_metadata(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
        extra_files={"simple-0.1.0.dist-info/METADATA": b"\xff"},
    )
    result = script.pip(
        "install", "--no-cache-dir", "--no-index", package, expect_error=True
    )
    assert "Error decoding metadata for" in result.stderr
    assert "simple-0.1.0-py2.py3-none-any.whl" in result.stderr
    assert "METADATA" in result.stderr


@pytest.mark.parametrize(
    "package_name",
    ["simple-package", "simple_package"],
)
def test_correct_package_name_while_creating_wheel_bug(script, package_name):
    """Check that the package name is correctly named while creating
    a .whl file with a given format
    """
    package = create_basic_wheel_for_package(script, package_name, "1.0")
    wheel_name = os.path.basename(package)
    assert wheel_name == "simple_package-1.0-py2.py3-none-any.whl"


@pytest.mark.parametrize("name", ["purelib", "abc"])
def test_wheel_with_file_in_data_dir_has_reasonable_error(script, tmpdir, name):
    """Normally we expect entities in the .data directory to be in a
    subdirectory, but if they are not then we should show a reasonable error
    message that includes the path.
    """
    wheel_path = make_wheel(
        "simple", "0.1.0", extra_data_files={name: "hello world"}
    ).save_to_dir(tmpdir)

    result = script.pip("install", "--no-index", str(wheel_path), expect_error=True)
    assert f"simple-0.1.0.data/{name}" in result.stderr


def test_wheel_with_unknown_subdir_in_data_dir_has_reasonable_error(script, tmpdir):
    wheel_path = make_wheel(
        "simple", "0.1.0", extra_data_files={"unknown/hello.txt": "hello world"}
    ).save_to_dir(tmpdir)

    result = script.pip("install", "--no-index", str(wheel_path), expect_error=True)
    assert "simple-0.1.0.data/unknown/hello.txt" in result.stderr
