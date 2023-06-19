from pip._internal.models.search_scope import SearchScope
from pip._internal.req.constructors import install_req_from_line


class TestSearchScope:
    def test_get_formatted_locations_basic_auth(self) -> None:
        """
        Test that basic authentication credentials defined in URL
        is not included in formatted output.
        """
        index_urls = [
            "https://pypi.org/simple",
            "https://repo-user:repo-pass@repo.domain.com",
        ]
        find_links = ["https://links-user:links-pass@page.domain.com"]
        search_scope = SearchScope(
            find_links=find_links,
            index_urls=index_urls,
            no_index=False,
        )

        result = search_scope.get_formatted_locations()
        assert "repo-user:****@repo.domain.com" in result
        assert "repo-pass" not in result
        assert "links-user:****@page.domain.com" in result
        assert "links-pass" not in result

    def test_get_index_urls_locations(self) -> None:
        """Check that the canonical name is on all indexes"""
        search_scope = SearchScope(
            find_links=[],
            index_urls=["file://index1/", "file://index2"],
            no_index=False,
        )
        req = install_req_from_line("Complex_Name")
        assert req.name is not None
        actual = search_scope.get_index_urls_locations(req.name)
        assert actual == [
            "file://index1/complex-name/",
            "file://index2/complex-name/",
        ]
