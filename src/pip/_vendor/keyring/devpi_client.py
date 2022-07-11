import contextlib

from pluggy import HookimplMarker

from pip._vendor import keyring
from pip._vendor.keyring.errors import KeyringError


hookimpl = HookimplMarker("devpiclient")


# https://github.com/jaraco/jaraco.context/blob/c3a9b739/jaraco/context.py#L205
suppress = type('suppress', (contextlib.suppress, contextlib.ContextDecorator), {})


@hookimpl()
@suppress(KeyringError)
def devpiclient_get_password(url, username):
    return keyring.get_password(url, username)
