import os
import sys
import re
import wsgi_intercept
from wsgi_intercept.urllib2_intercept import install_opener


PYPI_DEFAULT_STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pypiserver")


def _test_get_similar_urls():
    assert get_similar_urls('/simple/initools') == '/simple/INITools'
    assert get_similar_urls('/simple/initools/0.2') == '/simple/INITools/0.2'
    assert get_similar_urls('/simple/setuptools_git') == '/simple/setuptools-git'
    assert get_similar_urls('/simple/setuptools_git/') == '/simple/setuptools-git/'
    assert get_similar_urls('/simple/setuptools_git/setuptools_git-0.3.4.tar.gz') == '/simple/setuptools-git/setuptools_git-0.3.4.tar.gz'



def get_similar_urls(url):
    r = re.search(r'/simple/([^/]+)', url)
    here = os.path.dirname(os.path.abspath(__file__))
    all_packages = os.listdir(os.path.join(here, 'pypiserver', 'simple'))
    if r:
        package_name = r.group(1)
        for package in all_packages:
            if re.match(package_name, package, re.IGNORECASE):
                return re.sub(package_name, package, url, 1)
            if re.match(package_name.replace('_', '-'), package):
                return re.sub(package_name, package, url, 1)
    return url

def pypi_app():
    def wsgi_app(environ, start_response):
        headers = [('Content-type', 'text/html')]
        path_tree = get_similar_urls(environ['PATH_INFO']).split('/')
        url = os.path.join(PYPI_DEFAULT_STATIC_PATH, *path_tree)
        filepath = url
        if environ['PATH_INFO'].endswith('.gz'):
            headers = [('Content-type', 'application/x-gtar')]
        else:
            filepath = os.path.join(url, 'index.html')
        start_response('200 OK', headers)
        if not os.path.exists(filepath):
                return ''
        return [open(filepath, 'rb').read()]
    return wsgi_app


def use_fake_pypi():
    # allow wsgi_intercept to work with urllib2 fakes
    install_opener()
    wsgi_intercept.add_wsgi_intercept('pypi.python.org', 80, pypi_app)


if __name__ == '__main__':
    _test_get_similar_urls()
