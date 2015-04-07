from pip._vendor.six.moves.urllib import parse as urllib_parse


class Index(object):
    """Represents an index of Python packages like PyPI or a custom index

    >>> PyPI.url
    'https://pypi.python.org/'
    >>> PyPI.simple_url
    'https://pypi.python.org/simple'
    >>> PyPI.pypi_url
    'https://pypi.python.org/pypi'
    >>> PyPI.pip_json_url
    'https://pypi.python.org/pypi/pip/json'
    >>> my_company_index = Index('https://devpi.my-company.com')
    >>> my_company_index.url
    'https://devpi.my-company.com'
    >>> my_company_index.simple_url
    'https://devpi.my-company.com/simple'
    >>> my_company_index.pypi_url
    'https://devpi.my-company.com/pypi'
    >>> my_company_index.pip_json_url
    'https://devpi.my-company.com/pypi/pip/json'
    """

    def __init__(self, url):
        self.url = url
        self.netloc = urllib_parse.urlsplit(url).netloc
        self.simple_url = self.url_to_path('simple')
        self.pypi_url = self.url_to_path('pypi')
        self.pip_json_url = self.url_to_path('pypi/pip/json')

    def url_to_path(self, path):
        """
        >>> PyPI.url_to_path('foo')
        'https://pypi.python.org/foo'
        >>> PyPI.url_to_path('/foo')
        'https://pypi.python.org/foo'
        >>> PyPI.url_to_path('/foo/bar')
        'https://pypi.python.org/foo/bar'
        >>> my_company_index = Index('https://devpi.my-company.com')
        >>> my_company_index.url_to_path('/foo/bar')
        'https://devpi.my-company.com/foo/bar'
        """
        return urllib_parse.urljoin(self.url, path)


PyPI = Index('https://pypi.python.org/')
