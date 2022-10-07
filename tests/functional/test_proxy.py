import ssl
from pathlib import Path
from typing import Any, Dict

import proxy
import pytest
from proxy.http.proxy import HttpProxyBasePlugin

from tests.conftest import CertFactory
from tests.lib import PipTestEnvironment, TestData
from tests.lib.server import (
    authorization_response,
    make_mock_server,
    package_page,
    server_running,
)


class AccessLogPlugin(HttpProxyBasePlugin):
    def on_access_log(self, context: Dict[str, Any]) -> None:
        print(context)


@pytest.mark.network
def test_proxy_overrides_env(
    script: PipTestEnvironment, capfd: pytest.CaptureFixture[str]
) -> None:
    with proxy.Proxy(
        port=8899,
        num_acceptors=1,
    ), proxy.Proxy(plugins=[AccessLogPlugin], port=8888, num_acceptors=1):
        script.environ["http_proxy"] = "127.0.0.1:8888"
        script.environ["https_proxy"] = "127.0.0.1:8888"
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
        out, _ = capfd.readouterr()
        assert "CONNECT" not in out


def test_proxy_does_not_override_netrc(
    script: PipTestEnvironment,
    data: TestData,
    cert_factory: CertFactory,
) -> None:
    cert_path = cert_factory()
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(cert_path, cert_path)
    ctx.load_verify_locations(cafile=cert_path)
    ctx.verify_mode = ssl.CERT_REQUIRED

    server = make_mock_server(ssl_context=ctx)
    server.mock.side_effect = [
        package_page(
            {
                "simple-3.0.tar.gz": "/files/simple-3.0.tar.gz",
            }
        ),
        authorization_response(data.packages / "simple-3.0.tar.gz"),
        authorization_response(data.packages / "simple-3.0.tar.gz"),
    ]

    url = f"https://{server.host}:{server.port}/simple"

    netrc = script.scratch_path / ".netrc"
    netrc.write_text(f"machine {server.host} login USERNAME password PASSWORD")
    with proxy.Proxy(port=8888, num_acceptors=1), server_running(server):
        script.environ["NETRC"] = netrc
        script.pip(
            "install",
            "--proxy",
            "http://127.0.0.1:8888",
            "--trusted-host",
            "127.0.0.1",
            "--no-cache-dir",
            "--index-url",
            url,
            "--cert",
            cert_path,
            "--client-cert",
            cert_path,
            "simple",
        )
        script.assert_installed(simple="3.0")
