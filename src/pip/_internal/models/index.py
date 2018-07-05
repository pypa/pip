from pip._vendor.six.moves.urllib import parse as urllib_parse


class Index(object):
    def __init__(self, url, file_storage_domain):
        self.url = url
        self.netloc = urllib_parse.urlsplit(url).netloc
        self.simple_url = self.url_to_path('simple')
        self.pypi_url = self.url_to_path('pypi')

        # This is part of a temporary hack used to block installs of PyPI
        # packages which depend on external urls only necessary until PyPI can
        # block such packages themselves
        self.file_storage_domain = file_storage_domain

    def url_to_path(self, path):
        return urllib_parse.urljoin(self.url, path)


PyPI = Index('https://pypi.org/', 'files.pythonhosted.org')
TestPyPI = Index('https://test.pypi.org/', 'test-files.pythonhosted.org')
