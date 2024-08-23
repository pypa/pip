import json

import pytest

from tests.lib import PipTestEnvironment, ScriptFactory, TestData


@pytest.fixture
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
        "simplewheel==1.0",
    )
    return script


def test_inspect_basic(simple_script: PipTestEnvironment) -> None:
    """
    Test default behavior of inspect command.
    """
    result = simple_script.pip("inspect")
    report = json.loads(result.stdout)
    installed = report["installed"]
    assert len(installed) == 5
    installed_by_name = {i["metadata"]["name"]: i for i in installed}
    assert installed_by_name.keys() == {
        "pip",
        "setuptools",
        "wheel",
        "coverage",
        "simplewheel",
    }
    assert installed_by_name["simplewheel"]["metadata"]["version"] == "1.0"
    assert installed_by_name["simplewheel"]["requested"] is True
    assert installed_by_name["simplewheel"]["installer"] == "pip"
    assert "environment" in report
