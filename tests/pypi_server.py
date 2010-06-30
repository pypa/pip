import os
import wsgi_intercept
import urllib
import webob
from UserDict import DictMixin
from wsgiproxy.exactproxy import proxy_exact_request
from webob.dec import wsgify
from wsgi_intercept.urllib2_intercept import install_opener


class HasEverythingProxiedWSGIIntercept(DictMixin):

    def __contains__(self, key):
        return True
    
    def __getitem__(self, item):
        return (PyPIProxy, '')


class PyPIProxy(object):

    CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests_cache")

    @classmethod
    def setup(cls):
        instance = cls()
        instance._create_cache_folder()
        instance._add_wsgi_intercepts()
        return instance

    @wsgify
    def __call__(self, request):
        response = request.get_response(proxy_exact_request)
        if self._is_a_request_to_cached_file(request):
            return self._get_cached_response(request)
        elif self._is_a_request_to_non_cached_file(request):
            self._cache_file(request, response)
        return response

    def _get_cache_filename(self, request):
        filename = urllib.quote(request.url,  '')
        return os.path.join(self.CACHE_PATH, filename)

    def _is_a_request_to_cached_file(self, request):
        return (os.path.exists(self._get_cache_filename(request)) and
                request.method == 'GET')

    def _get_cached_response(self, request):
        fp = open(self._get_cache_filename(request), 'rb')
        response = webob.Response.from_file(fp)
        fp.close()
        return response

    def _cache_file(self, request, response):
        fp = open(self._get_cache_filename(request), 'wb')
        fp.write(str(response))
        fp.close()

    def _is_a_request_to_non_cached_file(self, request):
        return (not os.path.exists(self._get_cache_filename(request)) and
                request.method == 'GET')

    def _add_wsgi_intercepts(self):
        """allow wsgi_intercept to work with urllib2 fakes"""
        wsgi_intercept._wsgi_intercept = HasEverythingProxiedWSGIIntercept()
        install_opener()

    def _create_cache_folder(self):
        if not os.path.exists(self.CACHE_PATH):
            os.mkdir(self.CACHE_PATH)
