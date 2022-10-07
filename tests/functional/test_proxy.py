from pathlib import Path
from typing import Any, Dict

import proxy
import pytest
from proxy.http.proxy import HttpProxyBasePlugin

from tests.lib import PipTestEnvironment


class AccessLogPlugin(HttpProxyBasePlugin):
    def on_access_log(self, context: Dict[str, Any]) -> None:
        print(context)


@pytest.mark.network
def test_no_proxy(
    script: PipTestEnvironment, capfd: pytest.CaptureFixture[str]
) -> None:
    with proxy.Proxy(port=8888, num_acceptors=1, plugins=[AccessLogPlugin]):
        script.environ["no_proxy"] = "1"
        result = script.pip(
            "download",
            "--proxy",
            "http://127.0.0.1:8888",
            "--trusted-host",
            "127.0.0.1",
            "-d",
            "pip_downloads",
            "INITools==0.1",
        )
        result.did_create(Path("scratch") / "pip_downloads" / "INITools-0.1.tar.gz")
        out, _ = capfd.readouterr()
        assert "CONNECT" not in out
