import pytest

from pip._internal.models.link import Link


class TestLink:

    @pytest.mark.parametrize('url, expected', [
        ('https://example.com/path/page.html', 'page.html'),
        # Test a quoted character.
        ('https://example.com/path/page%231.html', 'page#1.html'),
        # Test a path that ends in a slash.
        ('https://example.com/path//', 'path'),
        # Test a url with no filename.
        ('https://example.com/', 'example.com'),
    ])
    def test_filename(self, url, expected):
        link = Link(url)
        assert link.filename == expected
