from typing import Any, Dict, Optional

import proxy
import pytest
from proxy.http.proxy import HttpProxyBasePlugin

from tests.lib import PipTestEnvironment
from tests.lib.path import Path


class AccessLogPlugin(HttpProxyBasePlugin):
    def on_access_log(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(context)
        return super().on_access_log(context)


@pytest.mark.network
def test_proxy_overrides_env(
    script: PipTestEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("http_proxy", "127:0.0.1:8888")
    monkeypatch.setenv("https_proxy", "127:0.0.1:8888")
    with proxy.Proxy(
        port=8899,
    ), proxy.Proxy(plugins=[AccessLogPlugin], port=8888):
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
        assert "CONNECT" not in result.stdout
