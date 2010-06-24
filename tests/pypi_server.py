import os
import re
import urllib2
import wsgi_intercept
import urllib
import webob
from wsgiproxy.exactproxy import proxy_exact_request
from webob.dec import wsgify
from wsgi_intercept.urllib2_intercept import install_opener


class PyPIProxy(object):

    CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pypi_cache")
    DOMAIN_NAMES_FILEPATH = os.path.join(CACHE_PATH, 'domains.txt')

    @classmethod
    def setup(cls):
        instance = cls()
        instance._monkey_patch_urllib2()
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

    def _monkey_patch_urllib2(self):
        urlopen = urllib2.urlopen
        def open_and_add_unknown_domains(arg):
            if isinstance(arg, basestring):
                self._store_domain(arg)
            else:
                self._store_domain(arg.get_full_url())
            return urlopen(arg)
        urllib2.urlopen = open_and_add_unknown_domains

    def _add_wsgi_intercepts(self):
        """allow wsgi_intercept to work with urllib2 fakes"""
        install_opener()
        domain_fp = open(PyPIProxy.DOMAIN_NAMES_FILEPATH)
        for line in domain_fp:
            wsgi_intercept.add_wsgi_intercept(line.strip(), 80, PyPIProxy)
        domain_fp.close()

    def _create_cache_folder(self):
        if not os.path.exists(self.CACHE_PATH):
            os.mkdir(self.CACHE_PATH)
            domain_fp = open(PyPIProxy.DOMAIN_NAMES_FILEPATH, 'w')
            domain_fp.write('pypi.python.org\n')
            domain_fp.close()

    def _store_domain(self, url):
        r = re.match(r'https?://([^/]+)', url)
        if not r:
            return
        domain_line = r.group(1) + '\n'
        if domain_line not in self._get_domains_to_be_intercepted():
            domain_fp = open(PyPIProxy.DOMAIN_NAMES_FILEPATH, 'a')
            domain_fp.write(domain_line)
            domain_fp.close()

    def _get_domains_to_be_intercepted(self):
        domain_fp = open(PyPIProxy.DOMAIN_NAMES_FILEPATH)
        domains = domain_fp.readlines()
        domain_fp.close()
        return domains
