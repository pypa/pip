"""HTMLPage: Represents one page, along with its URL."""

from __future__ import absolute_import

import cgi
import logging
import os
import re

from pip.models.link import Link
from pip.utils import cached_property
from pip._vendor import html5lib, requests
from pip._vendor.requests.exceptions import SSLError
from pip._vendor.six.moves.urllib import parse as urllib_parse
from pip._vendor.six.moves.urllib import request as urllib_request


logger = logging.getLogger(__name__)


class HTMLPage(object):
    """Represents one page, along with its URL"""

    # FIXME: these regexes are horrible hacks:
    _homepage_re = re.compile(b'<th>\\s*home\\s*page', re.I)
    _download_re = re.compile(b'<th>\\s*download\\s+url', re.I)
    _href_re = re.compile(
        b'href=(?:"([^"]*)"|\'([^\']*)\'|([^>\\s\\n]*))',
        re.I | re.S
    )

    def __init__(self, content, url, headers=None, trusted=None):
        # Determine if we have any encoding information in our headers
        encoding = None
        if headers and "Content-Type" in headers:
            content_type, params = cgi.parse_header(headers["Content-Type"])

            if "charset" in params:
                encoding = params['charset']

        self.content = content
        self.parsed = html5lib.parse(
            self.content,
            encoding=encoding,
            namespaceHTMLElements=False,
        )
        self.url = url
        self.headers = headers
        self.trusted = trusted

    def __str__(self):
        return self.url

    @classmethod
    def get_page(cls, link, req, skip_archives=True, session=None):
        if session is None:
            raise TypeError(
                "get_page() missing 1 required keyword argument: 'session'"
            )

        url = link.url
        url = url.split('#', 1)[0]

        # Check for VCS schemes that do not support lookup as web pages.
        from pip.vcs import VcsSupport
        for scheme in VcsSupport.schemes:
            if url.lower().startswith(scheme) and url[len(scheme)] in '+:':
                logger.debug('Cannot look at %s URL %s', scheme, link)
                return None

        try:
            if skip_archives:
                filename = link.filename
                for bad_ext in ['.tar', '.tar.gz', '.tar.bz2', '.tgz', '.zip']:
                    if filename.endswith(bad_ext):
                        content_type = cls._get_content_type(
                            url, session=session,
                        )
                        if content_type.lower().startswith('text/html'):
                            break
                        else:
                            logger.debug(
                                'Skipping page %s because of Content-Type: %s',
                                link,
                                content_type,
                            )
                            return

            logger.debug('Getting page %s', url)

            # Tack index.html onto file:// URLs that point to directories
            (scheme, netloc, path, params, query, fragment) = \
                urllib_parse.urlparse(url)
            if (scheme == 'file' and
                    os.path.isdir(urllib_request.url2pathname(path))):
                # add trailing slash if not present so urljoin doesn't trim
                # final segment
                if not url.endswith('/'):
                    url += '/'
                url = urllib_parse.urljoin(url, 'index.html')
                logger.debug(' file: URL is directory, getting %s', url)

            resp = session.get(
                url,
                headers={
                    "Accept": "text/html",
                    "Cache-Control": "max-age=600",
                },
            )
            resp.raise_for_status()

            # The check for archives above only works if the url ends with
            #   something that looks like an archive. However that is not a
            #   requirement of an url. Unless we issue a HEAD request on every
            #   url we cannot know ahead of time for sure if something is HTML
            #   or not. However we can check after we've downloaded it.
            content_type = resp.headers.get('Content-Type', 'unknown')
            if not content_type.lower().startswith("text/html"):
                logger.debug(
                    'Skipping page %s because of Content-Type: %s',
                    link,
                    content_type,
                )
                return

            inst = cls(
                resp.content, resp.url, resp.headers,
                trusted=link.trusted,
            )
        except requests.HTTPError as exc:
            level = 2 if exc.response.status_code == 404 else 1
            cls._handle_fail(req, link, exc, url, level=level)
        except requests.ConnectionError as exc:
            cls._handle_fail(
                req, link, "connection error: %s" % exc, url,
            )
        except requests.Timeout:
            cls._handle_fail(req, link, "timed out", url)
        except SSLError as exc:
            reason = ("There was a problem confirming the ssl certificate: "
                      "%s" % exc)
            cls._handle_fail(
                req, link, reason, url,
                level=2,
                meth=logger.info,
            )
        else:
            return inst

    @staticmethod
    def _handle_fail(req, link, reason, url, level=1, meth=None):
        if meth is None:
            meth = logger.debug

        meth("Could not fetch URL %s: %s", link, reason)
        meth("Will skip URL %s when looking for download links for %s" %
             (link.url, req))

    @staticmethod
    def _get_content_type(url, session):
        """Get the Content-Type of the given url, using a HEAD request"""
        scheme, netloc, path, query, fragment = urllib_parse.urlsplit(url)
        if scheme not in ('http', 'https'):
            # FIXME: some warning or something?
            # assertion error?
            return ''

        resp = session.head(url, allow_redirects=True)
        resp.raise_for_status()

        return resp.headers.get("Content-Type", "")

    @cached_property
    def api_version(self):
        metas = [
            x for x in self.parsed.findall(".//meta")
            if x.get("name", "").lower() == "api-version"
        ]
        if metas:
            try:
                return int(metas[0].get("value", None))
            except (TypeError, ValueError):
                pass

        return None

    @cached_property
    def base_url(self):
        bases = [
            x for x in self.parsed.findall(".//base")
            if x.get("href") is not None
        ]
        if bases and bases[0].get("href"):
            return bases[0].get("href")
        else:
            return self.url

    @property
    def links(self):
        """Yields all links in the page"""
        for anchor in self.parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(
                    urllib_parse.urljoin(self.base_url, href)
                )

                # Determine if this link is internal. If that distinction
                #   doesn't make sense in this context, then we don't make
                #   any distinction.
                internal = None
                if self.api_version and self.api_version >= 2:
                    # Only api_versions >= 2 have a distinction between
                    #   external and internal links
                    internal = bool(
                        anchor.get("rel") and
                        "internal" in anchor.get("rel").split()
                    )

                yield Link(url, self, internal=internal)

    def rel_links(self):
        for url in self.explicit_rel_links():
            yield url
        for url in self.scraped_rel_links():
            yield url

    def explicit_rel_links(self, rels=('homepage', 'download')):
        """Yields all links with the given relations"""
        rels = set(rels)

        for anchor in self.parsed.findall(".//a"):
            if anchor.get("rel") and anchor.get("href"):
                found_rels = set(anchor.get("rel").split())
                # Determine the intersection between what rels were found and
                #   what rels were being looked for
                if found_rels & rels:
                    href = anchor.get("href")
                    url = self.clean_link(
                        urllib_parse.urljoin(self.base_url, href)
                    )
                    yield Link(url, self, trusted=False)

    def scraped_rel_links(self):
        # Can we get rid of this horrible horrible method?
        for regex in (self._homepage_re, self._download_re):
            match = regex.search(self.content)
            if not match:
                continue
            href_match = self._href_re.search(self.content, pos=match.end())
            if not href_match:
                continue
            url = (
                href_match.group(1) or
                href_match.group(2) or
                href_match.group(3)
            )
            if not url:
                continue
            try:
                url = url.decode("ascii")
            except UnicodeDecodeError:
                continue
            url = self.clean_link(urllib_parse.urljoin(self.base_url, url))
            yield Link(url, self, trusted=False, _deprecated_regex=True)

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)

    def clean_link(self, url):
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self._clean_re.sub(
            lambda match: '%%%2x' % ord(match.group(0)), url)
