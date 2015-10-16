"""
Tests for the proxy support in pip.
"""

import pip

from tests.lib import SRC_DIR
from tests.lib.path import Path


def test_correct_pip_version():
    """
    Check we are importing pip from the right place.

    """
    assert Path(pip.__file__).folder.folder.abspath == SRC_DIR


def test_proxy_detection_and_url_with_embedded_login_password():
    """
    Ensure that we can call the proxy detection even if embedded login/password
    make the url too long.
    This may happen with localshop mirror.
    """
    url = "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:" \
        "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy@localhost/simple/"
    from pip._vendor.requests.utils import get_environ_proxies
    get_environ_proxies(url)
