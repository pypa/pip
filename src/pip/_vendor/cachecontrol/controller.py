# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The httplib2 algorithms ported for use with requests.
"""

from __future__ import annotations

import calendar
import logging
import re
import time
import weakref
from contextlib import closing
from email.utils import parsedate_tz
from typing import TYPE_CHECKING, Collection, Mapping

from pip._vendor.requests.structures import CaseInsensitiveDict

from pip._vendor.cachecontrol.cache import DictCache, SeparateBodyBaseCache
from pip._vendor.cachecontrol.serialize import Serializer

if TYPE_CHECKING:
    from typing import Literal

    from pip._vendor.requests import PreparedRequest
    from pip._vendor.urllib3 import HTTPResponse

    from pip._vendor.cachecontrol.cache import BaseCache

logger = logging.getLogger(__name__)

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")

PERMANENT_REDIRECT_STATUSES = (301, 308)


def parse_uri(uri: str) -> tuple[str, str, str, str, str]:
    """Parses a URI using the regex given in Appendix B of RFC 3986.

    (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    match = URI.match(uri)
    assert match is not None
    groups = match.groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController:
    """An interface to see if request should cached or not."""

    def __init__(
        self,
        cache: BaseCache | None = None,
        cache_etags: bool = True,
        serializer: Serializer | None = None,
        status_codes: Collection[int] | None = None,
    ):
        self.cache = DictCache() if cache is None else cache
        self.cache_etags = cache_etags
        self.serializer = serializer or Serializer()
        self.cacheable_status_codes = status_codes or (200, 203, 300, 301, 308)

    @classmethod
    def _urlnorm(cls, uri: str) -> str:
        """Normalize the URL to create a safe key for the cache"""
        (scheme, authority, path, query, fragment) = parse_uri(uri)
        if not scheme or not authority:
            raise Exception("Only absolute URIs are allowed. uri = %s" % uri)

        scheme = scheme.lower()
        userinfo, separator, host = authority.rpartition("@")
        authority = f"{userinfo}{separator}{host.lower()}"

        if not path:
            path = "/"

        # Could do syntax based normalization of the URI before
        # computing the digest. See Section 6.2.2 of Std 66.
        request_uri = query and "?".join([path, query]) or path
        defrag_uri = scheme + "://" + authority + request_uri

        return defrag_uri

    @classmethod
    def cache_url(cls, uri: str) -> str:
        return cls._urlnorm(uri)

    def parse_cache_control(self, headers: Mapping[str, str]) -> dict[str, int | None]:
        known_directives = {
            # https://tools.ietf.org/html/rfc7234#section-5.2
            "max-age": (int, True),
            "max-stale": (int, False),
            "min-fresh": (int, True),
            "no-cache": (None, False),
            "no-store": (None, False),
            "no-transform": (None, False),
            "only-if-cached": (None, False),
            "must-revalidate": (None, False),
            "public": (None, False),
            "private": (None, False),
            "proxy-revalidate": (None, False),
            "s-maxage": (int, True),
        }

        cc_headers = headers.get("cache-control", headers.get("Cache-Control", ""))

        retval: dict[str, int | None] = {}

        for cc_directive in cc_headers.split(","):
            if not cc_directive.strip():
                continue

            parts = cc_directive.split("=", 1)
            directive = parts[0].strip().lower()

            try:
                typ, required = known_directives[directive]
            except KeyError:
                logger.debug("Ignoring unknown cache-control directive: %s", directive)
                continue

            if not typ or not required:
                retval[directive] = None
            if typ:
                try:
                    retval[directive] = typ(parts[1].strip())
                except IndexError:
                    if required:
                        logger.debug(
                            "Missing value for cache-control directive: %s",
                            directive,
                        )
                except ValueError:
                    logger.debug(
                        "Invalid value for cache-control directive %s, must be %s",
                        directive,
                        typ.__name__,
                    )

        return retval

    def _load_from_cache(self, request: PreparedRequest) -> HTTPResponse | None:
        """
        Load a cached response, or return None if it's not available.
        """
        # We do not support caching of partial content: so if the request contains a
        # Range header then we don't want to load anything from the cache.
        if "Range" in request.headers:
            return None

        cache_url = request.url
        assert cache_url is not None
        cache_data = self.cache.get(cache_url)
        if cache_data is None:
            logger.debug("No cache entry available")
            return None

        if isinstance(self.cache, SeparateBodyBaseCache):
            body_file = self.cache.get_body(cache_url)
        else:
            body_file = None

        result: HTTPResponse | None = None
        try:
            result = self.serializer.loads(request, cache_data, body_file)
        finally:
            if result is None and body_file is not None:
                body_file.close()
        if result is None:
            logger.debug("Cache entry deserialization failed, entry ignored")
        return result

    def cached_request(self, request: PreparedRequest) -> HTTPResponse | Literal[False]:
        """
        Return a cached response if it exists in the cache, otherwise
        return False.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Looking up "%s" in the cache', cache_url)
        cc = self.parse_cache_control(request.headers)

        # Bail out if the request insists on fresh data
        if "no-cache" in cc:
            logger.debug('Request header has "no-cache", cache bypassed')
            return False

        if "max-age" in cc and cc["max-age"] == 0:
            logger.debug('Request header has "max_age" as 0, cache bypassed')
            return False

        # Check whether we can load the response from the cache:
        resp = self._load_from_cache(request)
        if not resp:
            return False

        keep_response = False
        try:
            headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)
            date_tuple = parsedate_tz(headers.get("date", ""))
            keep_response = date_tuple is not None and self._is_fresh(
                resp, headers, cc, calendar.timegm(date_tuple[:6])
            )
        finally:
            if not keep_response:
                resp.close()

        if keep_response:
            return resp

        if date_tuple is None:
            if "date" in headers:
                # Keep entries with unparseable dates available for revalidation.
                logger.debug("Ignoring cached response: invalid date")
                return False
            logger.debug("Ignoring cached response: no date")

        if "etag" not in headers:
            logger.debug("Purging cached response: stale or missing date, with no ETag")
            self.cache.delete(cache_url)
        return False

    def _is_fresh(
        self,
        resp: HTTPResponse,
        headers: Mapping[str, str],
        request_cc: Mapping[str, int | None],
        date: int,
    ) -> bool:
        current_age = max(0, time.time() - date)
        logger.debug("Current age based on date: %i", current_age)

        # Apply normal freshness checks to every cached response. In the case
        # of permanent redirects, RFC 9110 sections 15.4.2 and 15.4.9 permit
        # heuristic caching, but RFC 9111 section 4.2.2 requires explicit
        # expiration to take precedence. The redirect fallback below is used
        # only when neither max-age nor Expires provides an expiration.
        resp_cc = self.parse_cache_control(headers)

        # determine freshness
        freshness_lifetime = 0

        # Check the max-age pragma in the cache control header
        max_age = resp_cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug("Freshness lifetime from max-age: %i", freshness_lifetime)

        # If there isn't a max-age, check for an expires header
        elif "expires" in headers:
            expires = parsedate_tz(headers["expires"])
            if expires is not None:
                expire_time = calendar.timegm(expires[:6]) - date
                freshness_lifetime = max(0, expire_time)
                logger.debug("Freshness lifetime from expires: %i", freshness_lifetime)

        # Permanent redirects are heuristically cacheable when the response
        # does not provide an explicit freshness lifetime.
        elif int(resp.status) in PERMANENT_REDIRECT_STATUSES:
            logger.debug("Returning cached permanent redirect response")
            return True

        # Determine if we are setting freshness limit in the
        # request. Note, this overrides what was in the response.
        max_age = request_cc.get("max-age")
        if max_age is not None:
            freshness_lifetime = max_age
            logger.debug(
                "Freshness lifetime from request max-age: %i", freshness_lifetime
            )

        min_fresh = request_cc.get("min-fresh")
        if min_fresh is not None:
            # adjust our current age by our min fresh
            current_age += min_fresh
            logger.debug("Adjusted current age from min-fresh: %i", current_age)

        # Return entry if it is fresh enough
        if freshness_lifetime > current_age:
            logger.debug('The response is "fresh", returning cached response')
            logger.debug("%i > %i", freshness_lifetime, current_age)
            return True

        return False

    def conditional_headers(self, request: PreparedRequest) -> dict[str, str]:
        resp = self._load_from_cache(request)
        if not resp:
            return {}
        with closing(resp):
            new_headers = {}
            headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(resp.headers)

            if "etag" in headers:
                new_headers["If-None-Match"] = headers["ETag"]

            if "last-modified" in headers:
                new_headers["If-Modified-Since"] = headers["Last-Modified"]

            return new_headers

    def _cache_set(
        self,
        cache_url: str,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
        expires_time: int | None = None,
    ) -> None:
        """Store the data in the cache.
        """
        if expires_time is not None and expires_time <= 0:
            # Already stale on arrival
            logger.debug("Purging cached response: expires in the past")
            self.cache.delete(cache_url)
            return

        if isinstance(self.cache, SeparateBodyBaseCache):
            # We pass in the body separately; just put a placeholder empty
            # string in the metadata.
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, b""),
                expires=expires_time,
            )
            # body is None can happen when, for example, we're only updating
            # headers, as is the case in update_cached_response().
            if body is not None:
                self.cache.set_body(cache_url, body)
        else:
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, body),
                expires=expires_time,
            )

    def cache_response(
        self,
        request: PreparedRequest,
        response_or_ref: HTTPResponse | weakref.ReferenceType[HTTPResponse],
        body: bytes | None = None,
        status_codes: Collection[int] | None = None,
    ) -> None:
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        if isinstance(response_or_ref, weakref.ReferenceType):
            response = response_or_ref()
            if response is None:
                # The weakref can be None only in case the user used streamed request
                # and did not consume or close it, and holds no reference to requests.Response.
                # In such case, we don't want to cache the response.
                return
        else:
            response = response_or_ref

        # From httplib2: Don't cache 206's since we aren't going to
        #                handle byte range requests
        cacheable_status_codes = status_codes or self.cacheable_status_codes
        if response.status not in cacheable_status_codes:
            logger.debug(
                "Status code %s not in %s", response.status, cacheable_status_codes
            )
            return

        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            date = calendar.timegm(time_tuple[:6]) if time_tuple is not None else 0
        else:
            date = 0

        # If we've been given a body, our response has a Content-Length, that
        # Content-Length is valid then we can check to see if the body we've
        # been given matches the expected size, and if it doesn't we'll just
        # skip trying to cache it.
        if (
            body is not None
            and "content-length" in response_headers
            and response_headers["content-length"].isdigit()
            and int(response_headers["content-length"]) != len(body)
        ):
            return

        cc_req = self.parse_cache_control(request.headers)
        cc = self.parse_cache_control(response_headers)

        assert request.url is not None
        cache_url = self.cache_url(request.url)
        logger.debug('Updating cache with response from "%s"', cache_url)

        # Delete it from the cache if we happen to have it stored there
        no_store = False
        if "no-store" in cc:
            no_store = True
            logger.debug('Response header has "no-store"')
        if "no-store" in cc_req:
            no_store = True
            logger.debug('Request header has "no-store"')
        if no_store and self.cache.get(cache_url):
            logger.debug('Purging existing cache entry to honor "no-store"')
            self.cache.delete(cache_url)
        if no_store:
            return

        # https://tools.ietf.org/html/rfc7234#section-4.1:
        # A Vary header field-value of "*" always fails to match.
        # Storing such a response leads to a deserialization warning
        # during cache lookup and is not allowed to ever be served,
        # so storing it can be avoided.
        if "*" in response_headers.get("vary", ""):
            logger.debug('Response header has "Vary: *"')
            return

        # If we've been given an etag, then keep the response
        if self.cache_etags and "etag" in response_headers:
            expires_time = 0
            if response_headers.get("expires"):
                expires = parsedate_tz(response_headers["expires"])
                if expires is not None:
                    expires_time = calendar.timegm(expires[:6]) - date

            expires_time = max(expires_time, 14 * 86400)

            logger.debug(f"etag object cached for {expires_time} seconds")
            logger.debug("Caching due to etag")
            self._cache_set(cache_url, request, response, body, expires_time)

        # Add to the cache any permanent redirects. We do this before looking
        # that the Date headers.
        elif int(response.status) in PERMANENT_REDIRECT_STATUSES:
            logger.debug("Caching permanent redirect")
            self._cache_set(cache_url, request, response, b"")

        # Add to the cache if the response headers demand it. If there
        # is no date header then we can't do anything about expiring
        # the cache.
        elif "date" in response_headers:
            time_tuple = parsedate_tz(response_headers["date"])
            if time_tuple is None:
                return
            date = calendar.timegm(time_tuple[:6])
            # cache when there is a max-age > 0
            max_age = cc.get("max-age")
            if max_age is not None and max_age > 0:
                logger.debug("Caching b/c date exists and max-age > 0")
                expires_time = max_age
                self._cache_set(
                    cache_url,
                    request,
                    response,
                    body,
                    expires_time,
                )

            # If the request can expire, it means we should cache it
            # in the meantime.
            elif "expires" in response_headers:
                if response_headers["expires"]:
                    expires = parsedate_tz(response_headers["expires"])
                    if expires is None:
                        # https://tools.ietf.org/html/rfc9111#section-5.3: an
                        # invalid Expires must be read as a time in the past.
                        expires_time = 0
                    else:
                        expires_time = calendar.timegm(expires[:6]) - date

                    # A non-positive lifetime here means the response arrived
                    # stale
                    logger.debug(
                        "Caching b/c of expires header. expires in {} seconds".format(
                            expires_time
                        )
                    )
                    self._cache_set(
                        cache_url,
                        request,
                        response,
                        body,
                        expires_time,
                    )

    def update_cached_response(
        self, request: PreparedRequest, response: HTTPResponse
    ) -> HTTPResponse:
        """On a 304 we will get a new set of headers that we want to
        update our cached value with, assuming we have one.

        This should only ever be called when we've sent an ETag and
        gotten a 304 as the response.
        """
        assert request.url is not None
        cache_url = self.cache_url(request.url)
        cached_response = self._load_from_cache(request)

        if not cached_response:
            # we didn't have a cached response
            return response

        try:
            # A 304 updates the headers while keeping the cached body and its length.
            cached_response.headers.update(
                {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() != "content-length"
                }
            )
            cached_response.status = 200
            self._cache_set(cache_url, request, cached_response)
        except BaseException:
            cached_response.close()
            raise

        return cached_response
