import contextlib
import subprocess
import sys
from typing import Iterator

import pytest

from tests.lib import PipTestEnvironment
from tests.lib.path import Path


@contextlib.contextmanager
def run_proxy_server() -> Iterator[None]:
    proc = subprocess.Popen([sys.executable, "-m", "proxy"])
    yield
    proc.kill()


@pytest.mark.network
def test_download_over_http_proxy(script: PipTestEnvironment) -> None:
    """
    It should download (in the scratch path) and not install if requested.
    """
    with run_proxy_server():
        result = script.pip(
            "download",
            "--proxy",
            "http://127.0.0.1:8899",
            "--trusted-host",
            "127.0.0.1",
            "-d",
            "pip_downloads",
            "INITools==0.1",
        )
        result.did_create(Path("scratch") / "pip_downloads" / "INITools-0.1.tar.gz")
