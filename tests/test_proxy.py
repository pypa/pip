"""
Tests for the proxy support in pip.

TODO shouldn't need to hack sys.path in here.

"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import os
import pip
import getpass
from pip.basecommand import get_proxy
from tests.test_pip import here


def new_getpass(prompt, answer='passwd'):
    print('%s%s' % (prompt, answer))
    return answer


def test_correct_pip_version():
    """
    Check we are importing pip from the right place.

    """
    base = os.path.dirname(here)
    assert pip.__file__.startswith(base), pip.__file__


def test_remove_proxy():
    """
    Test removing proxy from environ.

    """
    if 'HTTP_PROXY' in os.environ:
        del os.environ['HTTP_PROXY']
    assert get_proxy() == None
    os.environ['HTTP_PROXY'] = 'user:pwd@server.com:port'
    assert get_proxy() == 'user:pwd@server.com:port'
    del os.environ['HTTP_PROXY']
    assert get_proxy('server.com') == 'server.com'
    assert get_proxy('server.com:80') == 'server.com:80'
    assert get_proxy('user:passwd@server.com:3128') == 'user:passwd@server.com:3128'


def test_get_proxy():
    """
    Test get_proxy returns correct proxy info.

    """
    # monkeypatch getpass.getpass, to avoid asking for a password
    old_getpass = getpass.getpass
    getpass.getpass = new_getpass

    # Test it:
    assert get_proxy('user:@server.com:3128') == 'user:@server.com:3128'
    assert get_proxy('user@server.com:3128') == 'user:passwd@server.com:3128'

    # Undo monkeypatch
    getpass.getpass = old_getpass

