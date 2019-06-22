import pytest

from pip._internal.models.link import Link


class TestLink:

    @pytest.mark.parametrize('url, expected', [
        ('http://yo/wheel.whl', 'wheel.whl'),
        ('http://yo/wheel', 'wheel'),
        ('https://example.com/path/page.html', 'page.html'),
        # Test a quoted character.
        ('https://example.com/path/page%231.html', 'page#1.html'),
        (
            'http://yo/myproject-1.0%2Bfoobar.0-py2.py3-none-any.whl',
            'myproject-1.0+foobar.0-py2.py3-none-any.whl',
        ),
        # Test a path that ends in a slash.
        ('https://example.com/path/', 'path'),
        ('https://example.com/path//', 'path'),
        # Test a url with no filename.
        ('https://example.com/', 'example.com'),
    ])
    def test_filename(self, url, expected):
        link = Link(url)
        assert link.filename == expected

    def test_splitext(self):
        assert ('wheel', '.whl') == Link('http://yo/wheel.whl').splitext()

    def test_no_ext(self):
        assert '' == Link('http://yo/wheel').ext

    def test_ext(self):
        assert '.whl' == Link('http://yo/wheel.whl').ext

    def test_ext_fragment(self):
        assert '.whl' == Link('http://yo/wheel.whl#frag').ext

    def test_ext_query(self):
        assert '.whl' == Link('http://yo/wheel.whl?a=b').ext

    def test_is_wheel(self):
        assert Link('http://yo/wheel.whl').is_wheel

    def test_is_wheel_false(self):
        assert not Link('http://yo/not_a_wheel').is_wheel

    def test_fragments(self):
        url = 'git+https://example.com/package#egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#egg=eggname&subdirectory=subdir'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#subdirectory=subdir&egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment
