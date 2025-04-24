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
    with (
        proxy.Proxy(port=0, num_acceptors=1) as proxy1,
        proxy.Proxy(plugins=[AccessLogPlugin], port=0, num_acceptors=1) as proxy2,
    ):
        script.environ["http_proxy"] = f"127.0.0.1:{proxy2.flags.port}"
        script.environ["https_proxy"] = f"127.0.0.1:{proxy2.flags.port}"
        result = script.pip(
            "download",
            "--proxy",
            f"http://127.0.0.1:{proxy1.flags.port}",
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
    with proxy.Proxy(port=0, num_acceptors=1) as proxy1, server_running(server):
        script.environ["NETRC"] = netrc
        script.pip(
            "install",
            "--proxy",
            f"http://127.0.0.1:{proxy1.flags.port}",
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


@pytest.mark.network
def test_build_deps_use_proxy_from_cli(
    script: PipTestEnvironment, capfd: pytest.CaptureFixture[str], data: TestData
) -> None:
    with proxy.Proxy(port=0, num_acceptors=1, plugins=[AccessLogPlugin]) as proxy1:
        result = script.pip(
            "wheel",
            "-v",
            str(data.packages / "pep517_setup_and_pyproject"),
            "--proxy",
            f"http://127.0.0.1:{proxy1.flags.port}",
        )

    wheel_path = script.scratch / "pep517_setup_and_pyproject-1.0-py3-none-any.whl"
    result.did_create(wheel_path)
    access_log, _ = capfd.readouterr()
    assert "CONNECT" in access_log, "setuptools was not fetched using proxy"
