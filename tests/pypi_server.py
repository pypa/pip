import os
import re
import wsgi_intercept
from wsgi_intercept.urllib2_intercept import install_opener


PYPI_DEFAULT_STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pypiserver")


def get_similar_pages(url):
    """
    >>> get_similar_pages('http://pypi.python.org/simple/initools')
    'http://pypi.python.org/simple/INITools'
    >>> get_similar_pages('http://pypi.python.org/simple/initools/0.2')
    'http://pypi.python.org/simple/INITools/0.2'
    >>> get_similar_pages('http://pypi.python.org/simple/setuptools_git')
    'http://pypi.python.org/simple/setuptools-git'
    >>> get_similar_pages('http://pypi.python.org/simple/setuptools_git/setuptools_git-0.3.4.tar.gz')
    'http://pypi.python.org/simple/setuptools-git/setuptools_git-0.3.4.tar.gz'
    """
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
        path_tree = environ['PATH_INFO'].split('/')
        url = os.path.join(PYPI_DEFAULT_STATIC_PATH, *path_tree)
        filepath = url
        if environ['PATH_INFO'].endswith('.gz'):
            headers = [('Content-type', 'application/x-gtar')]
        else:
            filepath = os.path.join(url, 'index.html')
        filepath = get_similar_pages(filepath)
        start_response('200 OK', headers)
        if not os.path.exists(filepath):
                return ''
        return [open(filepath, 'rb').read()]
    return wsgi_app


def use_fake_pypi():
    # allow wsgi_intercept to work with urllib2 fakes
    install_opener()
    wsgi_intercept.add_wsgi_intercept('pypi.python.org', 80, pypi_app)
