import json
import subprocess
import sys
import time
from typing import Any, Dict, Generator, List

import pytest

from tests.lib import PipTestEnvironment

ambigious_prerelease_resolution = (
    "Spec is ambigious, and uv and pip do not agree: "
    "https://github.com/astral-sh/packse/issues/160"
)
requires_different_python_version = (
    "Don't support this test yet with the way pip tests work. Probably "
    "need some kind of support from packse, written up a couple of "
    "issues that would allow it to be supported: "
    "https://github.com/astral-sh/packse/issues/164 "
    "https://github.com/astral-sh/packse/issues/163"
)
not_served_as_yanked = (
    "There seems to be an issue with packse serve right now where "
    "yanked packages are not showing as yanked in the simple api: "
    "https://github.com/astral-sh/packse/issues/165"
)

EXPECTED_TO_FAIL = {
    "example": (
        "Expected solution looks wrong: "
        "https://github.com/astral-sh/packse/issues/157"
    ),
    "local-not-used-with-sdist": (
        "Tests that sdist versions are preferred over local versions. "
        "Discussed: https://github.com/astral-sh/packse/issues/158. "
        "TODO: Find if this is a known issue on pip and/or packaging"
    ),
    "local-transitive-confounding": (
        "Expected solution looks wrong: "
        "https://github.com/astral-sh/packse/issues/159"
    ),
    "transitive-prerelease-and-stable-dependency": (ambigious_prerelease_resolution),
    "transitive-prerelease-and-stable-dependency-many-versions": (
        ambigious_prerelease_resolution
    ),
    "transitive-package-only-prereleases-in-range-opt-in": (
        ambigious_prerelease_resolution
    ),
    "package-only-prereleases-boundary": (
        "Expected solution is probably wrong: "
        "https://github.com/astral-sh/packse/issues/161"
    ),
    "package-prereleases-specifier-boundary": (requires_different_python_version),
    "python-greater-than-current": (requires_different_python_version),
    "python-greater-than-current-patch": (requires_different_python_version),
    "python-greater-than-current-backtrack": (requires_different_python_version),
    "python-greater-than-current-excluded": (requires_different_python_version),
    "compatible-python-incompatible-override": (requires_different_python_version),
    "incompatible-python-compatible-override-unavailable-no-wheels": (
        requires_different_python_version
    ),
    "incompatible-python-compatible-override-no-compatible-wheels": (
        requires_different_python_version
    ),
    "incompatible-python-compatible-override-other-wheel": (
        requires_different_python_version
    ),
    "python-patch-override-no-patch": (requires_different_python_version),
    "package-only-yanked": (not_served_as_yanked),
    "package-only-yanked-in-range": (not_served_as_yanked),
    "requires-package-yanked-and-unyanked-any": (not_served_as_yanked),
    "package-yanked-specified-mixed-available": (not_served_as_yanked),
    "transitive-package-only-yanked": (not_served_as_yanked),
    "transitive-package-only-yanked-in-range": (not_served_as_yanked),
    "transitive-yanked-and-unyanked-dependency": (not_served_as_yanked),
}


def run_command(command: List[str], cwd: None = None) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    result.check_returncode()
    return result.stdout.strip()


@pytest.fixture(scope="session", autouse=True)
def start_packse_server() -> Generator[None, None, None]:
    """Starts the packse server before tests run and ensures it's terminated after."""
    proc = subprocess.Popen(
        ["packse", "serve", "--host", "127.0.0.1", "--port", "3141"]
    )
    time.sleep(1)
    yield
    proc.terminate()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Dynamically parameterize tests based on scenarios fetched from packse."""
    if "scenario" in metafunc.fixturenames:
        # Fetch scenarios using packse
        scenarios_json: str = run_command(["packse", "inspect", "scenarios"])
        scenarios = json.loads(scenarios_json)

        # Prepare scenarios for parameterization, marking some as XFAIL
        scenarios_for_param = []
        ids_for_param = []
        for scenario in scenarios["scenarios"]:
            if scenario["name"] in EXPECTED_TO_FAIL:
                mark = pytest.mark.xfail(reason=EXPECTED_TO_FAIL[scenario["name"]])
                scenario_data = pytest.param(scenario, marks=mark)
            else:
                scenario_data = scenario
            scenarios_for_param.append(scenario_data)
            ids_for_param.append(scenario["name"])

        # Parameterize the test function with the prepared scenarios and IDs
        metafunc.parametrize("scenario", scenarios_for_param, ids=ids_for_param)


@pytest.mark.network
@pytest.mark.skipif(sys.version_info < (3, 12), reason="requires Python 3.12 or higher")
def test_packse_scenario(script: PipTestEnvironment, scenario: Dict[str, Any]) -> None:
    """Dynamically generated test for each packse scenario."""
    expected_satisfiable: bool = scenario["expected"]["satisfiable"]
    requirements: list[str] = [r["requirement"] for r in scenario["root"]["requires"]]

    resolver_options = []
    if scenario["resolver_options"]["prereleases"]:
        resolver_options.append("--pre")
    if scenario["resolver_options"]["no_build"]:
        resolver_options.append("--only-binary")
        resolver_options.append(",".join(scenario["resolver_options"]["no_build"]))
    if scenario["resolver_options"]["no_binary"]:
        resolver_options.append("--no-binary")
        resolver_options.append(",".join(scenario["resolver_options"]["no_binary"]))

    # Install the package as per the scenario setup
    result = script.pip(
        "install",
        "--index-url=http://127.0.0.1:3141/simple",
        *resolver_options,
        *requirements,
        allow_error=True,
    )

    resolution_failure_message = (
        "ERROR: Could not find a version that satisfies the requirement",
        "ERROR: ResolutionImpossible",
        "ERROR: Cannot install",
        "requires a different Python:",
    )

    if expected_satisfiable:
        assert "ERROR" not in result.stderr
        expected_installed = {
            p["name"]: p["version"] for p in scenario["expected"]["packages"]
        }
        script.assert_installed(**expected_installed)
    else:
        assert any(error in result.stderr for error in resolution_failure_message)
