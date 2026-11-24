from collections.abc import Callable
from typing import Any

import pytest

from tests.lib import PipTestEnvironment, TestPipResult

PipRunner = Callable[..., TestPipResult]


@pytest.fixture
def pip_no_truststore(script: PipTestEnvironment) -> PipRunner:
    def pip(*args: str, **kwargs: Any) -> TestPipResult:
        return script.pip(*args, "--use-deprecated=legacy-certs", **kwargs)

    return pip


@pytest.fixture
def pip_mixed_certs(script: PipTestEnvironment) -> PipRunner:
    def pip(*args: str, **kwargs: Any) -> TestPipResult:
        return script.pip(*args, "--use-deprecated=legacy-mixed-certs", **kwargs)

    return pip


@pytest.mark.network
@pytest.mark.parametrize(
    "package",
    [
        "INITools",
        "https://github.com/pypa/pip-test-package/archive/refs/heads/master.zip",
    ],
    ids=["PyPI", "GitHub"],
)
def test_no_truststore_can_install(
    script: PipTestEnvironment,
    pip_no_truststore: PipRunner,
    package: str,
) -> None:
    result = pip_no_truststore("install", package)
    assert "Successfully installed" in result.stdout


@pytest.mark.network
@pytest.mark.parametrize(
    "package",
    [
        "INITools",
        "https://github.com/pypa/pip-test-package/archive/refs/heads/master.zip",
    ],
    ids=["PyPI", "GitHub"],
)
def test_mixed_certs_can_install(
    script: PipTestEnvironment,
    pip_mixed_certs: PipRunner,
    package: str,
) -> None:
    result = pip_mixed_certs("install", package)
    assert "Successfully installed" in result.stdout
