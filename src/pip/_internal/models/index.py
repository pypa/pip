from pip._vendor.six.moves.urllib import parse as urllib_parse


class PackageIndex(object):
    """Represents a Package Index and provides easier access to endpoints
    """

    def __init__(self, url):
        super(PackageIndex, self).__init__()

        self.url = url
        self.netloc = urllib_parse.urlsplit(url).netloc
        self.simple_url = self._url_for_path('simple')
        self.pypi_url = self._url_for_path('pypi')

    def _url_for_path(self, path):
        return urllib_parse.urljoin(self.url, path)


PyPI = PackageIndex('https://pypi.org/')
