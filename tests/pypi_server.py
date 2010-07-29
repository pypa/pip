import urllib
import urllib2
import os
from UserDict import DictMixin


urlopen_original = urllib2.urlopen


class IgnoringCaseDict(DictMixin):

    def __init__(self):
        self._dict = dict()

    def __getitem__(self, key):
        return self._dict[key.lower()]

    def __setitem__(self, key, value):
        self._dict[key.lower()] = value

    def keys(self):
        return self._dict.keys()


class CachedResponse(object):
    """
    CachedResponse always cache url access and returns the cached response.
    It returns an object compatible with ``urllib.addinfourl``,
    it means the object is like the result of a call like::

        >>> response = urllib2.urlopen('http://example.com')
    """

    def __init__(self, url, folder):
        self.headers = IgnoringCaseDict() # maybe use httplib.HTTPMessage ??
        self.code = 500
        self.msg = 'Internal Server Error'
        # url can be a simple string, or a urllib2.Request object
        if isinstance(url, basestring):
            self.url = url
        else:
            self.url = url.get_full_url()
            self.headers.update(url.headers)
        self._body = ''
        self._set_all_fields(folder)

    def _set_all_fields(self, folder):
        filename = os.path.join(folder, urllib.quote(self.url, ''))
        if not os.path.exists(filename):
            self._cache_url(filename)
        fp = open(filename, 'rb')
        try:
            line = fp.next().strip()
            self.code, self.msg = line.split(None, 1)
        except ValueError:
            raise ValueError('Bad field line: %r' % line)
        self.code = int(self.code)
        for line in fp:
            if line == '\n':
                break
            key, value = line.split(': ')
            self.headers[key] = value.strip()
        for line in fp:
            self._body += line
        fp.close()

    def getcode(self):
        return self.code

    def geturl(self):
        return self.url

    def info(self):
        return self.headers

    def read(self, bytes=None):
        """
        it can read a chunk of bytes or everything
        """
        if bytes:
            result = self._body[:bytes]
            self._body = self._body[bytes:]
            return result
        return self._body

    def close(self):
        pass

    def _cache_url(self, filepath):
        response = urlopen_original(self.url)
        fp = open(filepath, 'wb')
        # when it uses file:// scheme, code is None and there is no msg attr
        # but it has been successfully opened
        status = '%s %s' % (getattr(response, 'code', 200) or 200, getattr(response, 'msg', 'OK'))
        headers = ['%s: %s' % (key, value) for key, value in response.headers.items()]
        body = response.read()
        fp.write('\n'.join([status] + headers + ['', body]))
        fp.close()


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
        urllib2.urlopen = urlopen

    def _create_cache_folder(self):
        if not os.path.exists(self.CACHE_PATH):
            os.mkdir(self.CACHE_PATH)


def test_cache_proxy():
    url = 'http://example.com'
    here = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(here, urllib.quote(url, ''))
    if os.path.exists(filepath):
        os.remove(filepath)
    response = urllib2.urlopen(url)
    r = CachedResponse(url, here)
    try:
        assert r.code == response.code
        assert r.msg == response.msg
        assert r.read() == response.read()
        assert r.url == response.url
        assert r.geturl() == response.geturl()
        assert r.headers.keys() == response.headers.keys()
        assert r.info().keys() == response.info().keys()
        assert r.headers['content-length'] == response.headers['content-length']
    finally:
        os.remove(filepath)
