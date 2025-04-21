from operator import index
from typing import List, Optional
from optparse import Values
import logging

from pip._internal.models.search_scope import SearchScope
from pip._internal.utils.misc import redact_auth_from_url

logger = logging.getLogger(__name__)

class IndexGroup:
    """An index group.

    Index groups are used to represent the possible sources of packages.
    In pip, there has long been one implicit IndexGroup: the collection
    of options that make up pip's package finder behavior.

    This class makes it simpler to have multiple index groups, which
    provides the opportunity to have multiple finders with different
    indexes and options, and to prioritize finders to prefer one over
    another.

    Within an index group, index urls and find-links are considered
    equal priority. Any consistent preference of one or the other is
    accidental and should not be relied on. The correct way to prioritize
    one index over another is to put the indexes in separate groups.
    """

    def __init__(self, index_urls: List[str], find_links: List[str], no_index: bool,
                 allow_yanked: bool, format_control: Optional["FormatControl"],
                 ignore_requires_python: bool, prefer_binary: bool
                 ) -> None:
        self.index_urls = index_urls
        self.find_links = find_links
        self.no_index = no_index
        self.format_control = format_control
        self.allow_yanked = allow_yanked
        self.ignore_requires_python = ignore_requires_python
        self.prefer_binary = prefer_binary


    @classmethod
    def create_(
            cls, options: Values,
    ) -> "IndexGroup":
        """
        Create an IndexGroup object from the given options and session.

        :param options: The options to use.
        """
        index_urls = options.get("index_url", [])
        if not index_urls:
            index_urls = [options.get("extra_index_url", [])]
        index_urls = [url for urls in index_urls for url in urls]

        find_links = options.get("find_links", [])
        if not find_links:
            find_links = options.get("find_links", [])
        find_links = [url for urls in find_links for url in urls]

        no_index = options.get("no_index", False)
        format_control = options.get("format_control", None)
        allow_yanked = options.get("allow_yanked", False)
        ignore_requires_python = options.get("ignore_requires_python", False)
        prefer_binary = options.get("prefer_binary", False)

        return cls(index_urls, find_links, no_index, allow_yanked, format_control,
                   ignore_requires_python, prefer_binary)

    def create_search_scope(self, suppress_no_index=False):
        index_urls = self.index_urls
        if self.no_index and not suppress_no_index:
            logger.debug(
                "Ignoring indexes: %s",
                ",".join(redact_auth_from_url(url) for url in self.index_urls),
            )
            index_urls = []

        return SearchScope.create(
            find_links=self.find_links,
            index_urls=index_urls,
            no_index=self.no_index,
        )
