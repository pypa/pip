from typing import Optional

import pytest

from pip._internal.models.link import Link, links_equivalent
from pip._internal.utils.hashes import Hashes


class TestLink:
    @pytest.mark.parametrize(
        "url, expected",
        [
            (
                "https://user:password@example.com/path/page.html",
                "<Link https://user:****@example.com/path/page.html>",
            ),
        ],
    )
    def test_repr(self, url: str, expected: str) -> None:
        link = Link(url)
        assert repr(link) == expected

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("http://yo/wheel.whl", "wheel.whl"),
            ("http://yo/wheel", "wheel"),
            ("https://example.com/path/page.html", "page.html"),
            # Test a quoted character.
            ("https://example.com/path/page%231.html", "page#1.html"),
            (
                "http://yo/myproject-1.0%2Bfoobar.0-py2.py3-none-any.whl",
                "myproject-1.0+foobar.0-py2.py3-none-any.whl",
            ),
            # Test a path that ends in a slash.
            ("https://example.com/path/", "path"),
            ("https://example.com/path//", "path"),
            # Test a url with no filename.
            ("https://example.com/", "example.com"),
            # Test a url with no filename and with auth information.
            (
                "https://user:password@example.com/",
                "example.com",
            ),
        ],
    )
    def test_filename(self, url: str, expected: str) -> None:
        link = Link(url)
        assert link.filename == expected

    def test_splitext(self) -> None:
        assert ("wheel", ".whl") == Link("http://yo/wheel.whl").splitext()

    def test_no_ext(self) -> None:
        assert "" == Link("http://yo/wheel").ext

    def test_ext(self) -> None:
        assert ".whl" == Link("http://yo/wheel.whl").ext

    def test_ext_fragment(self) -> None:
        assert ".whl" == Link("http://yo/wheel.whl#frag").ext

    def test_ext_query(self) -> None:
        assert ".whl" == Link("http://yo/wheel.whl?a=b").ext

    def test_is_wheel(self) -> None:
        assert Link("http://yo/wheel.whl").is_wheel

    def test_is_wheel_false(self) -> None:
        assert not Link("http://yo/not_a_wheel").is_wheel

    def test_fragments(self) -> None:
        url = "git+https://example.com/package#egg=eggname"
        assert "eggname" == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = "git+https://example.com/package#egg=eggname&subdirectory=subdir"
        assert "eggname" == Link(url).egg_fragment
        assert "subdir" == Link(url).subdirectory_fragment
        url = "git+https://example.com/package#subdirectory=subdir&egg=eggname"
        assert "eggname" == Link(url).egg_fragment
        assert "subdir" == Link(url).subdirectory_fragment

        # Extras are supported and preserved in the egg fragment,
        # even the empty extras specifier.
        # This behavior is deprecated and will change in pip 25.
        url = "git+https://example.com/package#egg=eggname[extra]"
        assert "eggname[extra]" == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = "git+https://example.com/package#egg=eggname[extra1,extra2]"
        assert "eggname[extra1,extra2]" == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = "git+https://example.com/package#egg=eggname[]"
        assert "eggname[]" == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment

    @pytest.mark.xfail(reason="Behavior change scheduled for 25.0", strict=True)
    @pytest.mark.parametrize(
        "fragment",
        [
            # Package names in egg fragments must be in PEP 508 form.
            "~invalid~package~name~",
            # Version specifiers are not valid in egg fragments.
            "eggname==1.2.3",
            "eggname>=1.2.3",
            # The extras specifier must be in PEP 508 form.
            "eggname[!]",
        ],
    )
    def test_invalid_egg_fragments(self, fragment: str) -> None:
        url = f"git+https://example.com/package#egg={fragment}"
        with pytest.raises(ValueError):
            Link(url)

    @pytest.mark.parametrize(
        "yanked_reason, expected",
        [
            (None, False),
            ("", True),
            ("there was a mistake", True),
        ],
    )
    def test_is_yanked(self, yanked_reason: Optional[str], expected: bool) -> None:
        link = Link(
            "https://example.com/wheel.whl",
            yanked_reason=yanked_reason,
        )
        assert link.is_yanked == expected

    @pytest.mark.parametrize(
        "hash_name, hex_digest, expected",
        [
            # Test a value that matches but with the wrong hash_name.
            ("sha384", 128 * "a", False),
            # Test matching values, including values other than the first.
            ("sha512", 128 * "a", True),
            ("sha512", 128 * "b", True),
            # Test a matching hash_name with a value that doesn't match.
            ("sha512", 128 * "c", False),
            # Test a link without a hash value.
            ("sha512", "", False),
        ],
    )
    def test_is_hash_allowed(
        self, hash_name: str, hex_digest: str, expected: bool
    ) -> None:
        url = f"https://example.com/wheel.whl#{hash_name}={hex_digest}"
        link = Link(url)
        hashes_data = {
            "sha512": [128 * "a", 128 * "b"],
        }
        hashes = Hashes(hashes_data)
        assert link.is_hash_allowed(hashes) == expected

    def test_is_hash_allowed__no_hash(self) -> None:
        link = Link("https://example.com/wheel.whl")
        hashes_data = {
            "sha512": [128 * "a"],
        }
        hashes = Hashes(hashes_data)
        assert not link.is_hash_allowed(hashes)

    @pytest.mark.parametrize(
        "hashes, expected",
        [
            (None, False),
            # Also test a success case to show the test is correct.
            (Hashes({"sha512": [128 * "a"]}), True),
        ],
    )
    def test_is_hash_allowed__none_hashes(
        self, hashes: Optional[Hashes], expected: bool
    ) -> None:
        url = "https://example.com/wheel.whl#sha512={}".format(128 * "a")
        link = Link(url)
        assert link.is_hash_allowed(hashes) == expected

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("git+https://github.com/org/repo", True),
            ("bzr+http://bzr.myproject.org/MyProject/trunk/#egg=MyProject", True),
            ("hg+file://hg.company.com/repo", True),
            ("https://example.com/some.whl", False),
            ("file://home/foo/some.whl", False),
        ],
    )
    def test_is_vcs(self, url: str, expected: bool) -> None:
        link = Link(url)
        assert link.is_vcs is expected


@pytest.mark.parametrize(
    "url1, url2",
    [
        pytest.param(
            "https://example.com/foo#egg=foo",
            "https://example.com/foo",
            id="drop-egg",
        ),
        pytest.param(
            "https://example.com/foo#subdirectory=bar&egg=foo",
            "https://example.com/foo#subdirectory=bar&egg=bar",
            id="drop-egg-only",
        ),
        pytest.param(
            "https://example.com/foo#subdirectory=bar&egg=foo",
            "https://example.com/foo#egg=foo&subdirectory=bar",
            id="fragment-ordering",
        ),
        pytest.param(
            "https://example.com/foo?a=1&b=2",
            "https://example.com/foo?b=2&a=1",
            id="query-opordering",
        ),
    ],
)
def test_links_equivalent(url1: str, url2: str) -> None:
    assert links_equivalent(Link(url1), Link(url2))


@pytest.mark.parametrize(
    "url1, url2",
    [
        pytest.param(
            "https://example.com/foo#sha512=1234567890abcdef",
            "https://example.com/foo#sha512=abcdef1234567890",
            id="different-keys",
        ),
        pytest.param(
            "https://example.com/foo#sha512=1234567890abcdef",
            "https://example.com/foo#md5=1234567890abcdef",
            id="different-values",
        ),
        pytest.param(
            "https://example.com/foo#subdirectory=bar&egg=foo",
            "https://example.com/foo#subdirectory=rex",
            id="drop-egg-still-different",
        ),
    ],
)
def test_links_equivalent_false(url1: str, url2: str) -> None:
    assert not links_equivalent(Link(url1), Link(url2))
