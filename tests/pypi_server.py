import httplib
import os
import base64
import urllib2
import pip.backwardcompat
from pip.backwardcompat import urllib, string_types, b, u, emailmessage


urlopen_original = pip.backwardcompat.urllib2.urlopen
build_opener_original = pip.backwardcompat.urllib2.build_opener


class HttpResponse(object):
    """
    Base class for HttpResponse
    It returns an object compatible with ``urllib.addinfourl``,
    it means the object is like the result of a call like::

        >>> response = urllib2.urlopen('http://example.com')
    """

    def __init__(self, url, **kwargs):
        self.headers = kwargs.pop('headers', emailmessage.Message())
        self.code = kwargs.pop('code', 200)
        self.msg = kwargs.pop('msg', '')
        # url can be a simple string, or a urllib2.Request object
        if isinstance(url, string_types):
            self.url = url
        else:
            self.url = url.get_full_url()
            for key, value in url.headers.items():
                self.headers[key] = value
        self._body = b('')

    def getcode(self):
        return self.code

    def geturl(self):
        return self.url

    def info(self):
        return self.headers

    def read(self, bytes=None):
        return self._body

    def readline(self):
        return ''

    def close(self):
        pass


class Response401(HttpResponse):
    def __init__(self, url, **kwargs):
        super(Response401, self).__init__(url, code=401, msg='Authorization Denied',
                                          headers={'www-authenticate': 'Basic realm="myRealm"'})

class CachedResponse(HttpResponse):
    """
    CachedResponse always cache url access and returns the cached response.
    """

    def __init__(self, url, folder):
        super(CachedResponse, self).__init__(url, headers = emailmessage.Message(), code=500, msg='Internal Server Error')
        self._set_all_fields(folder)

    def _set_all_fields(self, folder):
        filename = os.path.join(folder, urllib.quote(self.url, ''))
        if not os.path.exists(filename):
            self._cache_url(filename)
        fp = open(filename, 'rb')
        try:
            line = fp.readline().strip()
            self.code, self.msg = line.split(None, 1)
        except ValueError:
            raise ValueError('Bad field line: %r' % line)
        self.code = int(self.code)
        self.msg = u(self.msg)
        for line in fp:
            if line == b('\n'):
                break
            key, value = line.split(b(': '), 1)
            self.headers[u(key)] = u(value.strip())
        for line in fp:
            self._body += line
        fp.close()

    def read(self, bytes=None):
        """
        it can read a chunk of bytes or everything
        """
        if bytes:
            result = self._body[:bytes]
            self._body = self._body[bytes:]
            return result
        return self._body

    def _cache_url(self, filepath):
        response = urlopen_original(self.url)
        fp = open(filepath, 'wb')
        # when it uses file:// scheme, code is None and there is no msg attr
        # but it has been successfully opened
        status = b('%s %s' % (getattr(response, 'code', 200) or 200, getattr(response, 'msg', 'OK')))
        headers = [b('%s: %s' % (key, value)) for key, value in list(response.headers.items())]
        body = response.read()
        fp.write(b('\n').join([status] + headers + [b(''), body]))
        fp.close()


class HTTPFilterHandler(urllib2.HTTPHandler):
    def __init__(self, debuglevel=0, **kwargs):
        self._debuglevel = debuglevel
        self.username = kwargs.pop('username', None)
        self.password = kwargs.pop('password', None)

    def http_open(self, req):
        if 'Authorization' in req.unredirected_hdrs:
            value = req.unredirected_hdrs['Authorization']
            uname, passwd = base64.b64decode(value.split()[1]).split(':')
            if uname == self.username and passwd == self.password:
                return self.do_open(httplib.HTTPConnection, req)

        return Response401(req)


class PyPIProxy(object):
    CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests_cache")

    @classmethod
    def setup(cls):
        instance = cls()
        instance._create_cache_folder()
        instance._monkey_patch_urllib2_to_cache_everything()

    def _monkey_patch_urllib2_to_cache_everything(self):
        def urlopen(url):
            return CachedResponse(url, self.CACHE_PATH)

        pip.backwardcompat.urllib2.urlopen = urlopen

    def _create_cache_folder(self):
        if not os.path.exists(self.CACHE_PATH):
            os.mkdir(self.CACHE_PATH)


class PyPIBasicAuthProxy(PyPIProxy):

    @classmethod
    def setup(cls, username, password):
        instance = cls()
        instance._create_cache_folder()
        instance._secure(username, password)

    def _secure(self, username, password):
        def urlopen(url):
            # force first authentication
            if url.origin_req_host == 'pypi.python.org':
                raise urllib2.HTTPError(url, 401, "Not Authorized", None, None)
            return CachedResponse(url, PyPIProxy.CACHE_PATH)

        def build_opener(*handlers):
            return build_opener_original(HTTPFilterHandler(username=username, password=password), *handlers)

        pip.backwardcompat.urllib2.build_opener = build_opener
        pip.backwardcompat.urllib2.urlopen = urlopen


def assert_equal(a, b):
    assert a == b, "\nexpected:\n%r\ngot:\n%r" % (b, a)


def test_cache_proxy():
    url = 'http://example.com'
    here = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(here, urllib.quote(url, ''))
    if os.path.exists(filepath):
        os.remove(filepath)
    response = pip.backwardcompat.urllib2.urlopen(url)
    r = CachedResponse(url, here)
    try:
        assert_equal(r.code, response.code)
        assert_equal(r.msg, response.msg)
        assert_equal(r.read(), response.read())
        assert_equal(r.url, response.url)
        assert_equal(r.geturl(), response.geturl())
        assert_equal(set(r.headers.keys()), set(response.headers.keys()))
        assert_equal(set(r.info().keys()), set(response.info().keys()))
        assert_equal(r.headers['content-length'], response.headers['content-length'])
    finally:
        os.remove(filepath)
