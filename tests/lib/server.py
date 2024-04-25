import pathlib
import ssl
import threading
from base64 import b64encode
from contextlib import ExitStack, contextmanager
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Iterator, List
from unittest.mock import Mock

from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
from werkzeug.serving import make_server as _make_server

from .compat import blocked_signals

if TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment

Body = Iterable[bytes]


class _MockServer(BaseWSGIServer):
    mock: Mock = Mock()


class _RequestHandler(WSGIRequestHandler):
    def make_environ(self) -> Dict[str, Any]:
        environ = super().make_environ()

        # From pallets/werkzeug#1469, will probably be in release after
        # 0.16.0.
        try:
            # binary_form=False gives nicer information, but wouldn't be
            # compatible with what Nginx or Apache could return.
            peer_cert = self.connection.getpeercert(binary_form=True)
            if peer_cert is not None:
                # Nginx and Apache use PEM format.
                environ["SSL_CLIENT_CERT"] = ssl.DER_cert_to_PEM_cert(
                    peer_cert,
                )
        except ValueError:
            # SSL handshake hasn't finished.
            self.server.log("error", "Cannot fetch SSL peer certificate info")
        except AttributeError:
            # Not using TLS, the socket will not have getpeercert().
            pass

        return environ


def _mock_wsgi_adapter(
    mock: Callable[["WSGIEnvironment", "StartResponse"], "WSGIApplication"]
) -> "WSGIApplication":
    """Uses a mock to record function arguments and provide
    the actual function that should respond.
    """

    def adapter(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:
        try:
            responder = mock(environ, start_response)
        except StopIteration:
            raise RuntimeError("Ran out of mocked responses.")
        return responder(environ, start_response)

    return adapter


def make_mock_server(**kwargs: Any) -> _MockServer:
    """Creates a mock HTTP(S) server listening on a random port on localhost.

    The `mock` property of the returned server provides and records all WSGI
    interactions, so one approach to testing could be

        server = make_mock_server()
        server.mock.side_effects = [
            page1,
            page2,
        ]

        with server_running(server):
            # ... use server...
            ...

        assert server.mock.call_count > 0
        call_args_list = server.mock.call_args_list

        # `environ` is a dictionary defined as per PEP 3333 with the associated
        # contents. Additional properties may be added by werkzeug.
        environ, _ = call_args_list[0].args
        assert environ["PATH_INFO"].startswith("/hello/simple")

    Note that the server interactions take place in a different thread, so you
    do not want to touch the server.mock within the `server_running` block.

    Note also for pip interactions that "localhost" is a "secure origin", so
    be careful using this for failure tests of `--trusted-host`.
    """
    kwargs.setdefault("request_handler", _RequestHandler)

    mock = Mock()
    app = _mock_wsgi_adapter(mock)
    server = _make_server("localhost", 0, app=app, **kwargs)
    server.mock = mock
    return server


@contextmanager
def server_running(server: BaseWSGIServer) -> Iterator[None]:
    """Context manager for running the provided server in a separate thread."""
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    with blocked_signals():
        thread.start()
    try:
        yield
    finally:
        server.shutdown()
        thread.join()


# Helper functions for making responses in a declarative way.


def text_html_response(text: str) -> "WSGIApplication":
    def responder(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/html; charset=UTF-8"),
            ],
        )
        return [text.encode("utf-8")]

    return responder


def html5_page(text: str) -> str:
    return (
        dedent(
            """
    <!DOCTYPE html>
    <html>
      <body>
        {}
      </body>
    </html>
    """
        )
        .strip()
        .format(text)
    )


def package_page(spec: Dict[str, str]) -> "WSGIApplication":
    def link(name: str, value: str) -> str:
        return f'<a href="{value}">{name}</a>'

    links = "".join(link(*kv) for kv in spec.items())
    return text_html_response(html5_page(links))


def file_response(path: pathlib.Path) -> "WSGIApplication":
    def responder(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(path.stat().st_size)),
            ],
        )
        return [path.read_bytes()]

    return responder


def authorization_response(path: pathlib.Path) -> "WSGIApplication":
    correct_auth = "Basic " + b64encode(b"USERNAME:PASSWORD").decode("ascii")

    def responder(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:
        if environ.get("HTTP_AUTHORIZATION") != correct_auth:
            start_response("401 Unauthorized", [("WWW-Authenticate", "Basic")])
            return ()
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(path.stat().st_size)),
            ],
        )
        return [path.read_bytes()]

    return responder


class MockServer:
    def __init__(self, server: _MockServer) -> None:
        self._server = server
        self._running = False
        self.context = ExitStack()

    @property
    def port(self) -> int:
        return self._server.port

    @property
    def host(self) -> str:
        return self._server.host

    def set_responses(self, responses: Iterable["WSGIApplication"]) -> None:
        assert not self._running, "responses cannot be set on running server"
        self._server.mock.side_effect = responses

    def start(self) -> None:
        assert not self._running, "running server cannot be started"
        self.context.enter_context(server_running(self._server))
        self.context.enter_context(self._set_running())

    @contextmanager
    def _set_running(self) -> Iterator[None]:
        self._running = True
        try:
            yield
        finally:
            self._running = False

    def stop(self) -> None:
        assert self._running, "idle server cannot be stopped"
        self.context.close()

    def get_requests(self) -> List[Dict[str, str]]:
        """Get environ for each received request."""
        assert not self._running, "cannot get mock from running server"
        # Legacy: replace call[0][0] with call.args[0]
        # when pip drops support for python3.7
        return [call[0][0] for call in self._server.mock.call_args_list]
