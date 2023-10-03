import sys
from typing import Any, Callable

import pytest

from tests.lib import PipTestEnvironment, TestPipResult

PipRunner = Callable[..., TestPipResult]


@pytest.fixture()
def pip(script: PipTestEnvironment) -> PipRunner:
    def pip(*args: str, **kwargs: Any) -> TestPipResult:
        return script.pip(*args, "--use-feature=truststore", **kwargs)

    return pip


@pytest.mark.skipif(sys.version_info >= (3, 10), reason="3.10 can run truststore")
def test_truststore_error_on_old_python(pip: PipRunner) -> None:
    result = pip(
        "install",
        "--no-index",
        "does-not-matter",
        expect_error=True,
    )
    assert "The truststore feature is only available for Python 3.10+" in result.stderr


@pytest.mark.skipif(sys.version_info < (3, 10), reason="3.10+ required for truststore")
@pytest.mark.network
@pytest.mark.parametrize(
    "package",
    [
        "INITools",
        "https://github.com/pypa/pip-test-package/archive/refs/heads/master.zip",
    ],
    ids=["PyPI", "GitHub"],
)
def test_trustore_can_install(
    script: PipTestEnvironment,
    pip: PipRunner,
    package: str,
) -> None:
    result = pip("install", package)
    assert "Successfully installed" in result.stdout
