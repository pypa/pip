import json
import os
from pathlib import Path

import pytest

from pip._internal.models.direct_url import DirectUrl, DirInfo

from tests.lib import (
    PipTestEnvironment,
    ScriptFactory,
    TestData,
    _create_test_package,
    create_test_package_with_setup,
    wheel,
)
from tests.lib.direct_url import get_created_direct_url_path


@pytest.fixture(scope="session")
def simple_script(
    tmpdir_factory: pytest.TempPathFactory,
    script_factory: ScriptFactory,
    shared_data: TestData,
) -> PipTestEnvironment:
    tmpdir = tmpdir_factory.mktemp("pip_test_package")
    script = script_factory(tmpdir.joinpath("workspace"))
    script.pip(
        "install",
        "-f",
        shared_data.find_links,
        "--no-index",
        "simple==1.0",
        "simple2==3.0",
    )
    return script


def test_basic_list(simple_script: PipTestEnvironment) -> None:
    """
    Test default behavior of list command without format specifier.

    """
    result = simple_script.pip("list")
    assert "simple     1.0" in result.stdout, str(result)
    assert "simple2    3.0" in result.stdout, str(result)


def test_verbose_flag(simple_script: PipTestEnvironment) -> None:
    """
    Test the list command with the '-v' option
    """
    result = simple_script.pip("list", "-v", "--format=columns")
    assert "Package" in result.stdout, str(result)
    assert "Version" in result.stdout, str(result)
    assert "Location" in result.stdout, str(result)
    assert "Installer" in result.stdout, str(result)
    assert "simple     1.0" in result.stdout, str(result)
    assert "simple2    3.0" in result.stdout, str(result)


def test_columns_flag(simple_script: PipTestEnvironment) -> None:
    """
    Test the list command with the '--format=columns' option
    """
    result = simple_script.pip("list", "--format=columns")
    assert "Package" in result.stdout, str(result)
    assert "Version" in result.stdout, str(result)
    assert "simple (1.0)" not in result.stdout, str(result)
    assert "simple     1.0" in result.stdout, str(result)
    assert "simple2    3.0" in result.stdout, str(result)


def test_format_priority(simple_script: PipTestEnvironment) -> None:
    """
    Test that latest format has priority over previous ones.
    """
    result = simple_script.pip(
        "list", "--format=columns", "--format=freeze", expect_stderr=True
    )
    assert "simple==1.0" in result.stdout, str(result)
    assert "simple2==3.0" in result.stdout, str(result)
    assert "simple     1.0" not in result.stdout, str(result)
    assert "simple2    3.0" not in result.stdout, str(result)

    result = simple_script.pip("list", "--format=freeze", "--format=columns")
    assert "Package" in result.stdout, str(result)
    assert "Version" in result.stdout, str(result)
    assert "simple==1.0" not in result.stdout, str(result)
    assert "simple2==3.0" not in result.stdout, str(result)
    assert "simple     1.0" in result.stdout, str(result)
    assert "simple2    3.0" in result.stdout, str(result)


def test_local_flag(simple_script: PipTestEnvironment) -> None:
    """
    Test the behavior of --local flag in the list command

    """
    result = simple_script.pip("list", "--local", "--format=json")
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)


def test_local_columns_flag(simple_script: PipTestEnvironment) -> None:
    """
    Test the behavior of --local --format=columns flags in the list command

    """
    result = simple_script.pip("list", "--local", "--format=columns")
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "simple (1.0)" not in result.stdout
    assert "simple  1.0" in result.stdout, str(result)


def test_multiple_exclude_and_normalization(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    req_path = wheel.make_wheel(name="Normalizable_Name", version="1.0").save_to_dir(
        tmpdir
    )
    script.pip("install", "--no-index", req_path)
    result = script.pip("list")
    print(result.stdout)
    assert "Normalizable_Name" in result.stdout
    assert "pip" in result.stdout
    result = script.pip("list", "--exclude", "normalizablE-namE", "--exclude", "pIp")
    assert "Normalizable_Name" not in result.stdout
    assert "pip" not in result.stdout


@pytest.mark.network
@pytest.mark.usefixtures("enable_user_site")
def test_user_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --user flag in the list command

    """
    script.pip("download", "setuptools", "wheel", "-d", data.packages)
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")
    script.pip("install", "-f", data.find_links, "--no-index", "--user", "simple2==2.0")
    result = script.pip("list", "--user", "--format=json")
    assert {"name": "simple", "version": "1.0"} not in json.loads(result.stdout)
    assert {"name": "simple2", "version": "2.0"} in json.loads(result.stdout)


@pytest.mark.network
@pytest.mark.usefixtures("enable_user_site")
def test_user_columns_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --user --format=columns flags in the list command

    """
    script.pip("download", "setuptools", "wheel", "-d", data.packages)
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")
    script.pip("install", "-f", data.find_links, "--no-index", "--user", "simple2==2.0")
    result = script.pip("list", "--user", "--format=columns")
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "simple2 (2.0)" not in result.stdout
    assert "simple2 2.0" in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --uptodate flag in the list command

    """
    script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "simple==1.0",
        "simple2==3.0",
    )
    script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--uptodate",
        "--format=json",
    )
    json_output = json.loads(result.stdout)
    for item in json_output:
        if "editable_project_location" in item:
            item["editable_project_location"] = "<location>"
    assert {"name": "simple", "version": "1.0"} not in json_output  # 3.0 is latest
    assert {
        "name": "pip-test-package",
        "version": "0.1.1",
        "editable_project_location": "<location>",
    } in json_output  # editables included
    assert {"name": "simple2", "version": "3.0"} in json_output


@pytest.mark.network
def test_uptodate_columns_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --uptodate --format=columns flag in the list command

    """
    script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "simple==1.0",
        "simple2==3.0",
    )
    script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--uptodate",
        "--format=columns",
    )
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "Editable project location" in result.stdout  # editables included
    assert "pip-test-package (0.1.1," not in result.stdout
    assert "pip-test-package 0.1.1" in result.stdout, str(result)
    assert "simple2          3.0" in result.stdout, str(result)


@pytest.mark.network
def test_outdated_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --outdated flag in the list command

    """
    script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "simple==1.0",
        "simple2==3.0",
        "simplewheel==1.0",
    )
    script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git@0.1#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--outdated",
        "--format=json",
    )
    json_output = json.loads(result.stdout)
    for item in json_output:
        if "editable_project_location" in item:
            item["editable_project_location"] = "<location>"
    assert {
        "name": "simple",
        "version": "1.0",
        "latest_version": "3.0",
        "latest_filetype": "sdist",
    } in json_output
    assert {
        "name": "simplewheel",
        "version": "1.0",
        "latest_version": "2.0",
        "latest_filetype": "wheel",
    } in json_output
    assert {
        "name": "pip-test-package",
        "version": "0.1",
        "latest_version": "0.1.1",
        "latest_filetype": "sdist",
        "editable_project_location": "<location>",
    } in json_output
    assert "simple2" not in {p["name"] for p in json_output}


@pytest.mark.network
def test_outdated_columns_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test the behavior of --outdated --format=columns flag in the list command

    """
    script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "simple==1.0",
        "simple2==3.0",
        "simplewheel==1.0",
    )
    script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git@0.1#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--outdated",
        "--format=columns",
    )
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "Latest" in result.stdout
    assert "Type" in result.stdout
    assert "simple (1.0) - Latest: 3.0 [sdist]" not in result.stdout
    assert "simplewheel (1.0) - Latest: 2.0 [wheel]" not in result.stdout
    assert "simple           1.0     3.0    sdist" in result.stdout, str(result)
    assert "simplewheel      1.0     2.0    wheel" in result.stdout, str(result)
    assert "simple2" not in result.stdout, str(result)  # 3.0 is latest


@pytest.fixture(scope="session")
def pip_test_package_script(
    tmpdir_factory: pytest.TempPathFactory,
    script_factory: ScriptFactory,
    shared_data: TestData,
) -> PipTestEnvironment:
    tmpdir = tmpdir_factory.mktemp("pip_test_package")
    script = script_factory(tmpdir.joinpath("workspace"))
    script.pip("install", "-f", shared_data.find_links, "--no-index", "simple==1.0")
    script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package",
    )
    return script


@pytest.mark.network
def test_editables_flag(pip_test_package_script: PipTestEnvironment) -> None:
    """
    Test the behavior of --editables flag in the list command
    """
    result = pip_test_package_script.pip("list", "--editable", "--format=json")
    result2 = pip_test_package_script.pip("list", "--editable")
    assert {"name": "simple", "version": "1.0"} not in json.loads(result.stdout)
    assert os.path.join("src", "pip-test-package") in result2.stdout


@pytest.mark.network
def test_exclude_editable_flag(pip_test_package_script: PipTestEnvironment) -> None:
    """
    Test the behavior of --editables flag in the list command
    """
    result = pip_test_package_script.pip("list", "--exclude-editable", "--format=json")
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)
    assert "pip-test-package" not in {p["name"] for p in json.loads(result.stdout)}


@pytest.mark.network
def test_editables_columns_flag(pip_test_package_script: PipTestEnvironment) -> None:
    """
    Test the behavior of --editables flag in the list command
    """
    result = pip_test_package_script.pip("list", "--editable", "--format=columns")
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "Editable project location" in result.stdout
    assert os.path.join("src", "pip-test-package") in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_editables_flag(
    pip_test_package_script: PipTestEnvironment, data: TestData
) -> None:
    """
    test the behavior of --editable --uptodate flag in the list command
    """
    result = pip_test_package_script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--editable",
        "--uptodate",
    )
    assert "simple" not in result.stdout
    assert os.path.join("src", "pip-test-package") in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_editables_columns_flag(
    pip_test_package_script: PipTestEnvironment, data: TestData
) -> None:
    """
    test the behavior of --editable --uptodate --format=columns flag in the
    list command
    """
    result = pip_test_package_script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--editable",
        "--uptodate",
        "--format=columns",
    )
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "Editable project location" in result.stdout
    assert os.path.join("src", "pip-test-package") in result.stdout, str(result)


@pytest.mark.network
def test_outdated_editables_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")
    result = script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git@0.1#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--editable",
        "--outdated",
    )
    assert "simple" not in result.stdout
    assert os.path.join("src", "pip-test-package") in result.stdout


@pytest.mark.network
def test_outdated_editables_columns_flag(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")
    result = script.pip(
        "install",
        "-e",
        "git+https://github.com/pypa/pip-test-package.git@0.1#egg=pip-test-package",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--editable",
        "--outdated",
        "--format=columns",
    )
    assert "Package" in result.stdout
    assert "Version" in result.stdout
    assert "Editable project location" in result.stdout
    assert os.path.join("src", "pip-test-package") in result.stdout, str(result)


def test_outdated_not_required_flag(script: PipTestEnvironment, data: TestData) -> None:
    """
    test the behavior of --outdated --not-required flag in the list command
    """
    script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "simple==2.0",
        "require_simple==1.0",
    )
    result = script.pip(
        "list",
        "-f",
        data.find_links,
        "--no-index",
        "--outdated",
        "--not-required",
        "--format=json",
    )
    assert [] == json.loads(result.stdout)


def test_outdated_pre(script: PipTestEnvironment, data: TestData) -> None:
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")

    # Let's build a fake wheelhouse
    script.scratch_path.joinpath("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / "wheelhouse"
    wheelhouse_path.joinpath("simple-1.1-py2.py3-none-any.whl").write_text("")
    wheelhouse_path.joinpath("simple-2.0.dev0-py2.py3-none-any.whl").write_text("")
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--format=json",
    )
    assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--outdated",
        "--format=json",
    )
    assert {
        "name": "simple",
        "version": "1.0",
        "latest_version": "1.1",
        "latest_filetype": "wheel",
    } in json.loads(result.stdout)
    result_pre = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--outdated",
        "--pre",
        "--format=json",
    )
    assert {
        "name": "simple",
        "version": "1.0",
        "latest_version": "2.0.dev0",
        "latest_filetype": "wheel",
    } in json.loads(result_pre.stdout)


def test_outdated_formats(script: PipTestEnvironment, data: TestData) -> None:
    """Test of different outdated formats"""
    script.pip("install", "-f", data.find_links, "--no-index", "simple==1.0")

    # Let's build a fake wheelhouse
    script.scratch_path.joinpath("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / "wheelhouse"
    wheelhouse_path.joinpath("simple-1.1-py2.py3-none-any.whl").write_text("")
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--format=freeze",
    )
    assert "simple==1.0" in result.stdout

    # Check columns
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--outdated",
        "--format=columns",
    )
    assert "Package Version Latest Type" in result.stdout
    assert "simple  1.0     1.1    wheel" in result.stdout

    # Check that freeze is not allowed
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--outdated",
        "--format=freeze",
        expect_error=True,
    )
    assert (
        "List format 'freeze' cannot be used with the --outdated option."
        in result.stderr
    )

    # Check json
    result = script.pip(
        "list",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--outdated",
        "--format=json",
    )
    assert json.loads(result.stdout) == [
        {
            "name": "simple",
            "version": "1.0",
            "latest_version": "1.1",
            "latest_filetype": "wheel",
        }
    ]


def test_not_required_flag(script: PipTestEnvironment, data: TestData) -> None:
    script.pip("install", "-f", data.find_links, "--no-index", "TopoRequires4")
    result = script.pip("list", "--not-required", expect_stderr=True)
    assert "TopoRequires4 " in result.stdout, str(result)
    assert "TopoRequires " not in result.stdout
    assert "TopoRequires2 " not in result.stdout
    assert "TopoRequires3 " not in result.stdout


def test_list_freeze(simple_script: PipTestEnvironment) -> None:
    """
    Test freeze formatting of list command

    """
    result = simple_script.pip("list", "--format=freeze")
    assert "simple==1.0" in result.stdout, str(result)
    assert "simple2==3.0" in result.stdout, str(result)


def test_list_json(simple_script: PipTestEnvironment) -> None:
    """
    Test json formatting of list command

    """
    result = simple_script.pip("list", "--format=json")
    data = json.loads(result.stdout)
    assert {"name": "simple", "version": "1.0"} in data
    assert {"name": "simple2", "version": "3.0"} in data


def test_list_path(tmpdir: Path, script: PipTestEnvironment, data: TestData) -> None:
    """
    Test list with --path.
    """
    result = script.pip("list", "--path", tmpdir, "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "2.0"} not in json_result

    script.pip_install_local("--target", tmpdir, "simple==2.0")
    result = script.pip("list", "--path", tmpdir, "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "2.0"} in json_result


@pytest.mark.usefixtures("enable_user_site")
def test_list_path_exclude_user(
    tmpdir: Path, script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test list with --path and make sure packages from --user are not picked
    up.
    """
    script.pip_install_local("--user", "simple2")
    script.pip_install_local("--target", tmpdir, "simple==1.0")

    result = script.pip("list", "--user", "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple2", "version": "3.0"} in json_result

    result = script.pip("list", "--path", tmpdir, "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "1.0"} in json_result


def test_list_path_multiple(
    tmpdir: Path, script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test list with multiple --path arguments.
    """
    path1 = tmpdir / "path1"
    os.mkdir(path1)
    path2 = tmpdir / "path2"
    os.mkdir(path2)

    script.pip_install_local("--target", path1, "simple==2.0")
    script.pip_install_local("--target", path2, "simple2==3.0")

    result = script.pip("list", "--path", path1, "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "2.0"} in json_result

    result = script.pip("list", "--path", path1, "--path", path2, "--format=json")
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "2.0"} in json_result
    assert {"name": "simple2", "version": "3.0"} in json_result


def test_list_skip_work_dir_pkg(script: PipTestEnvironment) -> None:
    """
    Test that list should not include package in working directory
    """

    # Create a test package and create .egg-info dir
    pkg_path = create_test_package_with_setup(script, name="simple", version="1.0")
    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    # List should not include package simple when run from package directory
    result = script.pip("list", "--format=json", cwd=pkg_path)
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "1.0"} not in json_result


def test_list_include_work_dir_pkg(script: PipTestEnvironment) -> None:
    """
    Test that list should include package in working directory
    if working directory is added in PYTHONPATH
    """

    # Create a test package and create .egg-info dir
    pkg_path = create_test_package_with_setup(script, name="simple", version="1.0")
    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    script.environ.update({"PYTHONPATH": pkg_path})

    # List should include package simple when run from package directory
    # when the package directory is in PYTHONPATH
    result = script.pip("list", "--format=json", cwd=pkg_path)
    json_result = json.loads(result.stdout)
    assert {"name": "simple", "version": "1.0"} in json_result


def test_list_pep610_editable(script: PipTestEnvironment) -> None:
    """
    Test that a package installed with a direct_url.json with editable=true
    is correctly listed as editable.
    """
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    result = script.pip("install", pkg_path)
    direct_url_path = get_created_direct_url_path(result, "testpkg")
    assert direct_url_path
    # patch direct_url.json to simulate an editable install
    with open(direct_url_path) as f:
        direct_url = DirectUrl.from_json(f.read())
    assert isinstance(direct_url.info, DirInfo)
    direct_url.info.editable = True
    with open(direct_url_path, "w") as f:
        f.write(direct_url.to_json())
    result = script.pip("list", "--format=json")
    for item in json.loads(result.stdout):
        if item["name"] == "testpkg":
            assert item["editable_project_location"]
            break
    else:
        pytest.fail("package 'testpkg' not found in pip list result")
