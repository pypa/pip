import os
import sys
import base64
import getpass
import tempfile
import textwrap
import mock
from unittest import TestCase
from pip.download import URLOpener
from pip.backwardcompat import urllib2, string_types, b, emailmessage, u, httplib
from tests.test_pip import (reset_env, run_pip, clear_environ,
                            write_file, get_env, TestPipEnvironment)
from nose.tools import assert_raises
from tests.path import Path

PYPIRC = r"""
[distutils]
index-servers =
    pypi

[pypi]
username:username
password:valid
repository=http://pypi.python.org/pypi/
"""

PIPCONF = r"""
[global]
timeout = 60
default-timeout = 60
respect-virtualenv = true

[install]
use-mirrors = false
"""


class Response(object):
    """
    Dummy HttpResponse
    It returns an object compatible with ``urllib.addinfourl``,
    it means the object is like the result of a call like::

        >>> response = urllib2.urlopen('http://example.com')
    """

    def __init__(self, url, **kwargs):
        self.headers = kwargs.get('headers', {})
        self.code = kwargs.get('code', 200)
        self.msg = kwargs.get('msh', 'OK')
        self.url = url.get_full_url()

        for key, value in url.headers.items():
            self.headers[key] = value
        self._body = b('')
        self.info = lambda: self.headers
        self.read = lambda: self._body
        self.readline = lambda: ''

    def __repr__(self):
        return self.msg


class Response401(Response):
    def __init__(self, url, **kwargs):
        super(Response401, self).__init__(url, code=401, msg='Authorization Denied',
                                          headers={'www-authenticate': 'Basic realm="myRealm"'})


class HTTP401Filter(urllib2.HTTPHandler):
    def http_open(self, req):
        # python2.5 store 'Authorization' in `headers`, >2.5 store in `unredirected_hdrs`
        auth = req.headers.get('Authorization',
                               req.unredirected_hdrs.get('Authorization', None))
        if auth:
            auth_type, encoded_value = auth.split()
            uname, passwd = base64.b64decode(b(encoded_value)).split(b(':'))
            if (uname, passwd) == (b('username'), b('valid')):
                ret = self.do_open(httplib.HTTPConnection, req)
                ret.headers['mocked-credentials'] = 'true'
                return ret
        return Response401(req)


original_urllib2_build_opener = urllib2.build_opener


def build_opener(*handlers):
    return original_urllib2_build_opener(HTTP401Filter(), *handlers)


class log_method(object):
    def __init__(self, meth):
        self.meth = meth
        self.invocations = 0

    def __call__(self, *args, **kwargs):
        self.invocations += 1
        return self.meth(*args, **kwargs)


class TestBasicAuth(TestCase):
    def setUp(self):
        super(TestBasicAuth, self).setUp()
        self.patch()
        fd, self.config_file = tempfile.mkstemp('-pip.cfg', 'test-')
        write_file(self.config_file, textwrap.dedent(PIPCONF))

        fd, self.pypirc_file = tempfile.mkstemp('-pypirc.cfg', 'test-')
        write_file(self.pypirc_file, textwrap.dedent(PYPIRC))

    def tearDown(self):
        self.revert_patch()
        super(TestBasicAuth, self).tearDown()

    def patch(self):
        self.old_getpass_getuser = getpass.getuser
        self.old_getpass_getpass = getpass.getpass
        self.old_urllib2_urlopen = urllib2.urlopen

        getpass.getuser = lambda prompt: 'username'
        getpass.getpass = lambda prompt: 'password'
        self._environ = dict(os.environ)
        os.environ = clear_environ(self._environ)

        patcher_build_opener = mock.patch('pip.backwardcompat.urllib2.build_opener', build_opener)
        patcher_get_pass = mock.patch('getpass.getpass', log_method(getpass.getpass))

        patcher_get_pass.start()
        patcher_build_opener.start()

    def revert_patch(self):
        """ revert the patches to python methods """
        getpass.getuser = self.old_getpass_getuser
        getpass.getpass = self.old_getpass_getpass

        os.environ.update(self._environ)
        mock.patch.stopall()

    def test_load_password(self):
        """
        load .pypirc stored credentials
        """
        os.environ['PIP_CONFIG_FILE'] = self.config_file
        os.environ['PIP_PYPIRC'] = self.pypirc_file

        o = URLOpener()
        o.setup()
        assert o.passman.passwd == {None: {(('pypi.python.org', '/'),): ('username', 'valid')}}

    def test_no_login(self):
        """
        Cannot login to pypi without valid credentials, but no errors
        """
        os.environ['PIP_CONFIG_FILE'] = self.config_file
        os.environ['PIP_PYPIRC'] = ''

        o = URLOpener()
        o.setup(prompting=False)
        assert_raises(urllib2.HTTPError, o.get_response, 'http://pypi.python.org/pypi?%3Aaction=login')

    def test_unparsable_pypirc(self):
        """
        Should fail silently even if pypirc is unreadable
        """
        fd, pypirc_file = tempfile.mkstemp('-pypirc.cfg', 'test-')
        write_file(pypirc_file, textwrap.dedent("""
        [distutils]
        error
        """))
        os.environ['PIP_CONFIG_FILE'] = self.config_file
        os.environ['PIP_PYPIRC'] = pypirc_file

        o = URLOpener()
        o.setup(prompting=False)
        assert_raises(urllib2.HTTPError, o.get_response, 'http://pypi.python.org/pypi?%3Aaction=login')
        assert o.passman.passwd == {}, str(o.passman.passwd)

    def test_prompting(self):
        """
        Prompt for password if no valid one found
        """
        os.environ['PIP_CONFIG_FILE'] = self.config_file
        os.environ['PIP_PYPIRC'] = ''
        invoked = False

        o = URLOpener()
        o.setup(prompting=True)
        assert_raises(urllib2.HTTPError, o.get_response, 'http://pypi.python.org/pypi?%3Aaction=login')
        assert getpass.getpass.invocations == 3


    def test_valid_auth(self):
        """
        Use .pypirc credentials to access password protected repository
        """
        os.environ['PIP_CONFIG_FILE'] = self.config_file
        os.environ['PIP_PYPIRC'] = self.pypirc_file
        # sanity check. we want to be sure the filter is running
        o = URLOpener()
        o.setup()
        response = o.get_response('http://pypi.python.org/simple')
        assert 'mocked-credentials' in response.headers

        environ = clear_environ(os.environ.copy())
        environ['PIP_CONFIG_FILE'] = self.config_file
        environ['PIP_PYPIRC'] = self.pypirc_file
        env = reset_env(environ)

        result = run_pip('install', 'INITools==0.1', '-d', '.', expect_error=True)
        assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
        assert env.site_packages / 'initools' not in result.files_created
