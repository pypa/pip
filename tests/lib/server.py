import os
import signal
import ssl
import threading
from base64 import b64encode
from contextlib import contextmanager
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Iterator
from unittest.mock import Mock

from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
from werkzeug.serving import make_server as _make_server

from .compat import nullcontext

if TYPE_CHECKING:
    from wsgi import StartResponse, WSGIApplication, WSGIEnvironment

Body = Iterable[bytes]


class MockServer(BaseWSGIServer):
    mock: Mock = Mock()


# Applies on Python 2 and Windows.
if not hasattr(signal, "pthread_sigmask"):
    # We're not relying on this behavior anywhere currently, it's just best
    # practice.
    blocked_signals = nullcontext
else:

    @contextmanager
    def blocked_signals():
        """Block all signals for e.g. starting a worker thread."""
        # valid_signals() was added in Python 3.8 (and not using it results
        # in a warning on pthread_sigmask() call)
        try:
            mask = signal.valid_signals()
        except AttributeError:
            mask = set(range(1, signal.NSIG))

        old_mask = signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        try:
            yield
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)


class _RequestHandler(WSGIRequestHandler):
    def make_environ(self):
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


def make_mock_server(**kwargs: Any) -> MockServer:
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


def index_page(spec: Dict[str, str]) -> "WSGIApplication":
    def link(name, value):
        return '<a href="{}">{}</a>'.format(value, name)

    links = "".join(link(*kv) for kv in spec.items())
    return text_html_response(html5_page(links))


def package_page(spec: Dict[str, str]) -> "WSGIApplication":
    def link(name, value):
        return '<a href="{}">{}</a>'.format(value, name)

    links = "".join(link(*kv) for kv in spec.items())
    return text_html_response(html5_page(links))


def file_response(path: str) -> "WSGIApplication":
    def responder(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:
        size = os.stat(path).st_size
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(size)),
            ],
        )

        with open(path, "rb") as f:
            return [f.read()]

    return responder


def authorization_response(path: str) -> "WSGIApplication":
    correct_auth = "Basic " + b64encode(b"USERNAME:PASSWORD").decode("ascii")

    def responder(environ: "WSGIEnvironment", start_response: "StartResponse") -> Body:

        if environ.get("HTTP_AUTHORIZATION") == correct_auth:
            size = os.stat(path).st_size
            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/octet-stream"),
                    ("Content-Length", str(size)),
                ],
            )
        else:
            start_response(
                "401 Unauthorized",
                [
                    ("WWW-Authenticate", "Basic"),
                ],
            )

        with open(path, "rb") as f:
            return [f.read()]

    return responder
