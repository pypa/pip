from pathlib import Path
from typing import Callable, Optional

import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS

from tests.lib import PipTestEnvironment
from tests.lib.wheel import make_wheel

MakeFakeWheel = Callable[[str], str]


@pytest.fixture
def make_fake_wheel(script: PipTestEnvironment) -> MakeFakeWheel:
    def _make_fake_wheel(wheel_tag: str) -> str:
        wheel_house = script.scratch_path.joinpath("wheelhouse")
        wheel_house.mkdir()
        wheel_builder = make_wheel(
            name="fake",
            version="1.0",
            wheel_metadata_updates={"Tag": []},
        )
        wheel_path = wheel_house.joinpath(f"fake-1.0-{wheel_tag}.whl")
        wheel_builder.save_to(wheel_path)
        return str(wheel_path)

    return _make_fake_wheel


@pytest.mark.parametrize("implementation", [None, "fakepy"])
@pytest.mark.parametrize("python_version", [None, "1"])
@pytest.mark.parametrize("abi", [None, "fakeabi"])
@pytest.mark.parametrize("platform", [None, "fakeplat"])
def test_new_resolver_target_checks_compatibility_failure(
    script: PipTestEnvironment,
    make_fake_wheel: MakeFakeWheel,
    implementation: Optional[str],
    python_version: Optional[str],
    abi: Optional[str],
    platform: Optional[str],
) -> None:
    fake_wheel_tag = "fakepy1-fakeabi-fakeplat"
    args = [
        "install",
        "--only-binary=:all:",
        "--no-cache-dir",
        "--no-index",
        "--target",
        str(script.scratch_path.joinpath("target")),
        make_fake_wheel(fake_wheel_tag),
    ]
    if implementation:
        args += ["--implementation", implementation]
    if python_version:
        args += ["--python-version", python_version]
    if abi:
        args += ["--abi", abi]
    if platform:
        args += ["--platform", platform]

    args_tag = f"{implementation}{python_version}-{abi}-{platform}"
    wheel_tag_matches = args_tag == fake_wheel_tag

    result = script.pip(*args, expect_error=(not wheel_tag_matches))

    dist_info = Path("scratch", "target", "fake-1.0.dist-info")
    if wheel_tag_matches:
        assert result.returncode == SUCCESS
        result.did_create(dist_info)
    else:
        assert result.returncode == ERROR
        result.did_not_create(dist_info)
