"""
Routines related to PyPI, indexes, PEP381 mirrors
"""
import sys
import os
import re
import gzip
import mimetypes
import threading
import posixpath
import pkg_resources
import random
import socket
import string
import zlib
from pip.locations import serverkey_file
from pip.log import logger

from pip.util import Inf, normalize_name, splitext
from pip.exceptions import DistributionNotFound, BestVersionAlreadyInstalled
from pip.backwardcompat import (WindowsError, BytesIO,
                                Queue, urlparse,
                                URLError, HTTPError, b, u,
                                product, url2pathname,
                                OrderedDict, _ord as ord,
                                decode_base64, _long,
                                Empty as QueueEmpty)
from pip.download import (urlopen, path_to_url2, url_to_path, geturl,
                          Urllib2HeadRequest)

__all__ = ['PackageFinder']


DEFAULT_MIRROR_URL = "last.pypi.python.org"


class PackageFinder(object):
    """
    This finds packages.

    This is meant to match easy_install's technique for looking for
    packages, by reading pages and looking for appropriate links
    """

    def __init__(self, find_links, index_urls, use_mirrors=False,
            mirrors=None, main_mirror_url=None):
        self.find_links = find_links
        self.index_urls = index_urls
        self.dependency_links = []
        self.cache = PageCache()
        # These are boring links that have already been logged somehow:
        self.logged_links = set()
        if use_mirrors:
            self.mirror_urls = self._get_mirror_urls(mirrors, main_mirror_url)
            logger.info('Using PyPI mirrors: %s' %
                        ', '.join([url.url for url in self.mirror_urls]))
        else:
            self.mirror_urls = ()
        serverkey_cache = open(serverkey_file, 'rb')
        try:
            self.serverkey = load_key(serverkey_cache.read())
        finally:
            serverkey_cache.close()

    def add_dependency_links(self, links):
        ## FIXME: this shouldn't be global list this, it should only
        ## apply to requirements of the package that specifies the
        ## dependency_links value
        ## FIXME: also, we should track comes_from (i.e., use Link)
        self.dependency_links.extend(links)

    @staticmethod
    def _sort_locations(locations):
        """
        Sort locations into "files" (archives) and "urls", and return
        a pair of lists (files, urls)
        """
        files = []
        urls = []

        # puts the url for the given file path into the appropriate
        # list
        def sort_path(url, path):
            new_url = path_to_url2(path)
            mimetype = mimetypes.guess_type(new_url, strict=False)[0]
            url.url = new_url
            if mimetype == 'text/html':
                urls.append(url)
            else:
                files.append(url)

        for url in locations:
            if isinstance(url, Link):
                url = url.copy()
            else:
                url = Link(url)
            if url.url.startswith('file:'):
                path = url_to_path(url.url)
                if os.path.isdir(path):
                    path = os.path.realpath(path)
                    for item in os.listdir(path):
                        sort_path(url, os.path.join(path, item))
                elif os.path.isfile(path):
                    sort_path(url, path)
            else:
                urls.append(url)
        return files, urls

    def make_package_url(self, url, name):
        """
        For maximum compatibility with easy_install, ensure the path
        ends in a trailing slash.  Although this isn't in the spec
        (and PyPI can handle it without the slash) some other index
        implementations might break if they relied on easy_install's
        behavior.
        """
        if isinstance(url, Link):
            package_url = url.copy()
        else:
            package_url = Link(url)
        new_url = posixpath.join(package_url.url, name)
        if not new_url.endswith('/'):
            new_url = new_url + '/'
        package_url.url = new_url
        return package_url

    def verify(self, requirement, url):
        """
        Verifies the URL for the given requirement using the PEP381
        verification code.
        """
        if url.comes_from:
            try:
                data = b(url.comes_from.content)
                if data and requirement.serversig:
                    return verify(self.serverkey, data, requirement.serversig)
            except ValueError:
                return False
        return False

    def find_requirement(self, req, upgrade):
        url_name = req.url_name
        # Only check main index if index URL is given:
        main_index_url = None
        if self.index_urls:
            # Check that we have the url_name correctly spelled:
            main_index_url = self.make_package_url(self.index_urls[0],
                                                   url_name)
            # This will also cache the page,
            # so it's okay that we get it again later:
            page = self._get_page(main_index_url, req)
            if page is None:
                url_name = self._find_url_name(
                    Link(self.index_urls[0]), url_name, req) or req.url_name

        # Combine index URLs with mirror URLs here to allow
        # adding more index URLs from requirements files

        locations = []
        indexes_package_urls = []
        mirrors_package_urls = []
        if url_name is not None:
            indexes_package_urls = [self.make_package_url(url, url_name)
                                    for url in self.index_urls]
            locations.extend(indexes_package_urls)
            mirrors_package_urls = [self.make_package_url(url, url_name)
                                    for url in self.mirror_urls]
            locations.extend(mirrors_package_urls)

        locations.extend(self.find_links + self.dependency_links)

        for version in req.absolute_versions:
            if url_name is not None and main_index_url is not None:
                version_url = posixpath.join(main_index_url.url, version)
                locations = [version_url] + locations

        file_locations, url_locations = self._sort_locations(locations)

        locations = []
        for url in url_locations:
            if isinstance(url, Link):
                locations.append(url)
            else:
                locations.append(Link(url))
        logger.debug('URLs to search for versions for %s:' % req)
        for location in locations:
            logger.debug('* %s' % location)

        found_versions = []
        found_versions.extend(self._package_versions(
            [Link(url, '-f') for url in self.find_links], req.name.lower()))

        page_versions = []
        for page in self._get_pages(locations, req):
            logger.debug('Analyzing links from page %s' % page.url)
            logger.indent += 2
            try:
                page_versions.extend(self._package_versions(
                    page.links, req.name.lower()))
            finally:
                logger.indent -= 2

        dependency_versions = list(self._package_versions(
            [Link(url) for url in self.dependency_links], req.name.lower()))
        if dependency_versions:
            dependency_urls = [link.url for _, link, _ in dependency_versions]
            logger.info('dependency_links found: %s' %
                        ', '.join(dependency_urls))

        file_versions = list(self._package_versions(
                [Link(url) for url in file_locations], req.name.lower()))
        if (not found_versions and not page_versions and
                not dependency_versions and not file_versions):
            logger.fatal('Could not find any downloads that satisfy '
                         'the requirement %s' % req)
            raise DistributionNotFound('No distributions at all found for %s'
                                       % req)

        if req.satisfied_by is not None:
            found_versions.append((req.satisfied_by.parsed_version,
                                   Inf, req.satisfied_by.version))

        if file_versions:
            file_versions.sort(reverse=True)
            file_urls = [url_to_path(link.url) for _, link, _ in file_versions]
            logger.info('Local files found: %s' % ', '.join(file_urls))
            found_versions = file_versions + found_versions

        all_versions = found_versions + page_versions + dependency_versions

        applicable_versions = OrderedDict()
        for parsed_version, link, version in all_versions:
            if version not in req.req:
                req_specs = [''.join(s) for s in req.req.specs]
                logger.info("Ignoring link %s, version %s doesn't match %s" %
                            (link, version, ','.join(req_specs)))
                continue
            if link.comes_from in mirrors_package_urls:
                link.is_mirror = True
            applicable_versions.setdefault(version, []).append(link)

        for version in applicable_versions:
            random.shuffle(applicable_versions[version])

        applicable_versions = OrderedDict(sorted(applicable_versions.items(),
            key=lambda v: pkg_resources.parse_version(v[0]), reverse=True))

        existing_applicable = bool([link for link in [links
                                    for links in applicable_versions.items()]
                                    if link is Inf])
        if not upgrade and existing_applicable:
            if Inf in applicable_versions:
                logger.info('Existing installed version (%s) is most '
                            'up-to-date and satisfies requirement' %
                            req.satisfied_by.version)
                raise BestVersionAlreadyInstalled
            else:
                logger.info('Existing installed version (%s) satisfies '
                            'requirement (most up-to-date version is %s)' %
                            (req.satisfied_by.version,
                             applicable_versions[0][1]))
            return None

        if not applicable_versions:
            show_versions = [version for _, _, version in found_versions]
            logger.fatal('Could not find a version that satisfies '
                         'the requirement %s (from versions: %s)' %
                         (req, ', '.join(show_versions)))
            raise DistributionNotFound('No distributions matching '
                                       'the version for %s' % req)

        newest = list(applicable_versions.keys())[0]
        if Inf in applicable_versions:
            # We have an existing version, and it's the best version
            show_versions = [vers for vers in applicable_versions.keys()[1:]]
            logger.info('Installed version (%s) is most up-to-date '
                        '(past versions: %s)' %
                        (req.satisfied_by.version,
                         ', '.join(show_versions) or 'none'))
            raise BestVersionAlreadyInstalled

        if len(applicable_versions) > 1:
            logger.info('Using version %s (newest of versions: %s)' %
                        (newest, ', '.join(applicable_versions.keys())))

        return applicable_versions[newest]

    def _find_url_name(self, index_url, url_name, req):
        """
        Finds the true URL name of a package, when the given name isn't
        quite correct. This is usually used to implement case-insensitivity.
        """
        if not index_url.url.endswith('/'):
            # Vaguely part of the PyPI API... weird but true.
            ## FIXME: bad to modify this?
            index_url.url += '/'
        page = self._get_page(index_url, req)
        if page is None:
            logger.fatal('Cannot fetch index base URL %s' % index_url)
            return
        norm_name = normalize_name(req.url_name)
        for link in page.links:
            base = posixpath.basename(link.path.rstrip('/'))
            if norm_name == normalize_name(base):
                logger.notify('Real name of requirement %s is %s' %
                              (url_name, base))
                return base
        return None

    def _get_pages(self, locations, req):
        """Yields (page, page_url) from the given locations, skipping
        locations that have errors, and adding download/homepage links"""
        pending_queue = Queue()
        for location in locations:
            pending_queue.put(location)
        done = []
        seen = set()
        threads = []
        for i in range(min(10, len(locations))):
            thread = threading.Thread(target=self._get_queued_page,
                                      args=(req, pending_queue, done, seen))
            thread.setDaemon(True)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        return done

    _log_lock = threading.Lock()

    def _get_queued_page(self, req, pending_queue, done, seen):
        while 1:
            try:
                location = pending_queue.get(False)
            except QueueEmpty:
                return
            if location in seen:
                continue
            seen.add(location)
            page = self._get_page(location, req)
            if page is None:
                continue
            done.append(page)
            for link in page.rel_links():
                pending_queue.put(link)

    _egg_fragment_re = re.compile(r'#egg=([^&]*)')
    _egg_info_re = re.compile(r'([a-z0-9_.]+)-([a-z0-9_.-]+)', re.I)
    _py_version_re = re.compile(r'-py([123]\.?[0-9]?)$')

    def _sort_links(self, links):
        """
        Returns elements of links in order, non-egg links first,
        egg links second, while eliminating duplicates
        """
        eggs, no_eggs = [], []
        seen = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                if link.egg_fragment:
                    eggs.append(link)
                else:
                    no_eggs.append(link)
        return no_eggs + eggs

    def _package_versions(self, links, search_name):
        for link in self._sort_links(links):
            for v in self._link_package_versions(link, search_name):
                yield v

    def _link_package_versions(self, link, search_name):
        """
        Return an iterable of triples (pkg_resources_version_key,
        link, python_version) that can be extracted from the given
        link.

        Meant to be overridden by subclasses, not called by clients.
        """
        if link.egg_fragment:
            egg_info = link.egg_fragment
        else:
            egg_info, ext = link.splitext()
            if not ext:
                if link not in self.logged_links:
                    logger.debug('Skipping link %s; not a file' % link)
                    self.logged_links.add(link)
                return []
            if egg_info.endswith('.tar'):
                # Special double-extension case:
                egg_info = egg_info[:-4]
                ext = '.tar' + ext
            if ext not in ('.tar.gz', '.tar.bz2', '.tar', '.tgz', '.zip'):
                if link not in self.logged_links:
                    logger.debug('Skipping link %s; unknown archive '
                                 'format: %s' % (link, ext))
                    self.logged_links.add(link)
                return []
            if "macosx10" in link.path and ext == '.zip':
                if link not in self.logged_links:
                    logger.debug('Skipping link %s; macosx10 one' % (link))
                    self.logged_links.add(link)
                return []
        version = self._egg_info_matches(egg_info, search_name, link)
        if version is None:
            logger.debug('Skipping link %s; wrong project name (not %s)' %
                         (link, search_name))
            return []
        match = self._py_version_re.search(version)
        if match:
            version = version[:match.start()]
            py_version = match.group(1)
            if py_version != sys.version[:3]:
                logger.debug('Skipping %s because Python '
                             'version is incorrect' % link)
                return []
        logger.debug('Found link %s, version: %s' % (link, version))
        return [(pkg_resources.parse_version(version),
               link,
               version)]

    def _egg_info_matches(self, egg_info, search_name, link):
        match = self._egg_info_re.search(egg_info)
        if not match:
            logger.debug('Could not parse version from link: %s' % link)
            return None
        name = match.group(0).lower()
        # To match the "safe" name that pkg_resources creates:
        name = name.replace('_', '-')
        if name.startswith(search_name.lower()):
            return match.group(0)[len(search_name):].lstrip('-')
        else:
            return None

    def _get_page(self, link, req):
        return HTMLPage.get_page(link, req, cache=self.cache)

    def _get_mirror_urls(self, mirrors=None, main_mirror_url=None):
        """
        Retrieves a list of URLs from the main mirror DNS entry
        unless a list of mirror URLs are passed.
        """
        if not mirrors:
            mirrors = get_mirrors(main_mirror_url)
            # Should this be made "less random"? E.g. netselect like?
            random.shuffle(mirrors)

        mirror_urls = set()
        for mirror_url in mirrors:
            # Make sure we have a valid URL
            if not ("http://" or "https://" or "file://") in mirror_url:
                mirror_url = "http://%s" % mirror_url
            if not mirror_url.endswith("/simple"):
                mirror_url = "%s/simple/" % mirror_url
            mirror_urls.add(mirror_url)

        return tuple(Link(url, is_mirror=True) for url in mirror_urls)


class PageCache(object):
    """Cache of HTML pages"""

    failure_limit = 3

    def __init__(self):
        self._failures = {}
        self._pages = {}
        self._archives = {}

    def too_many_failures(self, url):
        return self._failures.get(url, 0) >= self.failure_limit

    def get_page(self, url):
        return self._pages.get(url)

    def is_archive(self, url):
        return self._archives.get(url, False)

    def set_is_archive(self, url, value=True):
        self._archives[url] = value

    def add_page_failure(self, url, level):
        self._failures[url] = self._failures.get(url, 0) + level

    def add_page(self, urls, page):
        for url in urls:
            self._pages[url] = page


class HTMLPage(object):
    """Represents one page, along with its URL"""

    ## FIXME: these regexes are horrible hacks:
    _homepage_re = re.compile(r'<th>\s*home\s*page', re.I)
    _download_re = re.compile(r'<th>\s*download\s+url', re.I)
    ## These aren't so aweful:
    _rel_re = re.compile("""<[^>]*\srel\s*=\s*['"]?([^'">]+)[^>]*>""", re.I)
    _href_re = re.compile('href=(?:"([^"]*)"|\'([^\']*)\'|([^>\\s\\n]*))',
                          re.I | re.S)
    _base_re = re.compile(r"""<base\s+href\s*=\s*['"]?([^'">]+)""", re.I)

    def __init__(self, content, url, headers=None):
        self.content = content
        self.url = url
        self.headers = headers

    def __str__(self):
        return self.url

    @classmethod
    def get_page(cls, link, req, cache=None, skip_archives=True):
        url = link.url
        url = url.split('#', 1)[0]
        if cache.too_many_failures(url):
            return None

        # Check for VCS schemes that do not support lookup as web pages.
        from pip.vcs import VcsSupport
        for scheme in VcsSupport.schemes:
            if url.lower().startswith(scheme) and url[len(scheme)] in '+:':
                logger.debug('Cannot look at %s URL %s' %
                             (scheme, link))
                return None

        if cache is not None:
            inst = cache.get_page(url)
            if inst is not None:
                return inst
        try:
            if skip_archives:
                if cache is not None:
                    if cache.is_archive(url):
                        return None
                filename = link.filename
                for bad_ext in ['.tar', '.tar.gz', '.tar.bz2', '.tgz', '.zip']:
                    if filename.endswith(bad_ext):
                        content_type = cls._get_content_type(url)
                        if content_type.lower().startswith('text/html'):
                            break
                        else:
                            logger.debug('Skipping page %s because of '
                                         'Content-Type: %s' %
                                         (link, content_type))
                            if cache is not None:
                                cache.set_is_archive(url)
                            return None
            logger.debug('Getting page %s' % url)

            # Tack index.html onto file:// URLs that point to directories
            parsed_url = urlparse.urlparse(url)
            scheme, netloc, path, params, query, fragment = parsed_url
            if scheme == 'file' and os.path.isdir(url2pathname(path)):
                # add trailing slash if not present so urljoin
                # doesn't trim final segment
                if not url.endswith('/'):
                    url += '/'
                url = urlparse.urljoin(url, 'index.html')
                logger.debug(' file: URL is directory, getting %s' % url)

            resp = urlopen(url)

            real_url = geturl(resp)
            headers = resp.info()
            contents = resp.read()
            encoding = headers.get('Content-Encoding', None)
            #XXX need to handle exceptions and add testing for this
            if encoding is not None:
                if encoding == 'gzip':
                    contents = gzip.GzipFile(fileobj=BytesIO(contents)).read()
                if encoding == 'deflate':
                    contents = zlib.decompress(contents)
            inst = cls(u(contents), real_url, headers)
        except (HTTPError, URLError, socket.timeout,
                socket.error, OSError, WindowsError):
            e = sys.exc_info()[1]
            desc = str(e)
            if isinstance(e, socket.timeout):
                log_meth = logger.info
                level = 1
                desc = 'timed out'
            elif isinstance(e, URLError):
                log_meth = logger.info
                if (hasattr(e, 'reason') and
                        isinstance(e.reason, socket.timeout)):
                    desc = 'timed out'
                    level = 1
                else:
                    level = 2
            elif isinstance(e, HTTPError) and e.code == 404:
                ## FIXME: notify?
                log_meth = logger.info
                level = 2
            else:
                log_meth = logger.info
                level = 1
            log_meth('Could not fetch URL %s: %s' % (link, desc))
            log_meth('Will skip URL %s when looking for '
                     'download links for %s' % (link.url, req))
            if cache is not None:
                cache.add_page_failure(url, level)
            return None
        if cache is not None:
            cache.add_page([url, real_url], inst)
        return inst

    @staticmethod
    def _get_content_type(url):
        """Get the Content-Type of the given url, using a HEAD request"""
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        if not scheme in ('http', 'https', 'ftp', 'ftps'):
            ## FIXME: some warning or something?
            ## assertion error?
            return ''
        req = Urllib2HeadRequest(url, headers={'Host': netloc})
        resp = urlopen(req)
        try:
            if (hasattr(resp, 'code') and
                resp.code != 200 and scheme not in ('ftp', 'ftps')):
                ## FIXME: doesn't handle redirects
                return ''
            return resp.info().get('content-type', '')
        finally:
            resp.close()

    @property
    def base_url(self):
        if not hasattr(self, "_base_url"):
            match = self._base_re.search(self.content)
            if match:
                self._base_url = match.group(1)
            else:
                self._base_url = self.url
        return self._base_url

    @property
    def links(self):
        """
        Yields all links in the page
        """
        for match in self._href_re.finditer(self.content):
            url = match.group(1) or match.group(2) or match.group(3)
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    def rel_links(self):
        for url in self.explicit_rel_links():
            yield url
        for url in self.scraped_rel_links():
            yield url

    def explicit_rel_links(self, rels=('homepage', 'download')):
        """
        Yields all links with the given relations
        """
        for match in self._rel_re.finditer(self.content):
            found_rels = match.group(1).lower().split()
            for rel in rels:
                if rel in found_rels:
                    break
            else:
                continue
            match = self._href_re.search(match.group(0))
            if not match:
                continue
            url = match.group(1) or match.group(2) or match.group(3)
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    def scraped_rel_links(self):
        for regex in (self._homepage_re, self._download_re):
            match = regex.search(self.content)
            if not match:
                continue
            href_match = self._href_re.search(self.content, pos=match.end())
            if not href_match:
                continue
            url = (href_match.group(1) or
                   href_match.group(2) or
                   href_match.group(3))
            if not url:
                continue
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%~_\\|-]', re.I)

    def clean_link(self, url):
        """
        Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters).
        """
        def replacer(match):
            matched_group = match.group(0)
            return '%%%2x' % ord(matched_group)
        return self._clean_re.sub(replacer, url.strip())


class Link(object):

    def __init__(self, url, comes_from=None, is_mirror=False):
        self.url = url
        self.comes_from = comes_from
        self.is_mirror = is_mirror

    def __str__(self):
        if self.comes_from:
            return '%s (from %s)' % (self.url, self.comes_from)
        else:
            return self.url

    def __repr__(self):
        return '<Link %s>' % self

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    @property
    def filename(self):
        url = self.url_fragment
        name = posixpath.basename(url)
        assert name, ('URL %r produced no filename' % url)
        return name

    @property
    def scheme(self):
        return urlparse.urlsplit(self.url)[0]

    @property
    def path(self):
        return urlparse.urlsplit(self.url)[2]

    def splitext(self):
        return splitext(posixpath.basename(self.path.rstrip('/')))

    @property
    def url_fragment(self):
        url = self.url
        url = url.split('#', 1)[0]
        url = url.split('?', 1)[0]
        url = url.rstrip('/')
        return url

    _egg_fragment_re = re.compile(r'#egg=([^&]*)')

    @property
    def egg_fragment(self):
        match = self._egg_fragment_re.search(self.url)
        if not match:
            return None
        return match.group(1)

    _md5_re = re.compile(r'md5=([a-f0-9]+)')

    @property
    def md5_hash(self):
        match = self._md5_re.search(self.url)
        if match:
            return match.group(1)
        return None

    @property
    def show_url(self):
        return posixpath.basename(self.url.split('#', 1)[0].split('?', 1)[0])

    def copy(self):
        return self.__class__(self.url, comes_from=self.comes_from,
                              is_mirror=self.is_mirror)


def get_requirement_from_url(url):
    """Get a requirement from the URL, if possible.  This looks for #egg
    in the URL"""
    link = Link(url)
    egg_info = link.egg_fragment
    if not egg_info:
        egg_info = splitext(link.filename)[0]
    return package_to_requirement(egg_info)


def package_to_requirement(package_name):
    """Translate a name like Foo-1.2 to Foo==1.3"""
    match = re.search(r'^(.*?)-(dev|\d.*)', package_name)
    if match:
        name = match.group(1)
        version = match.group(2)
    else:
        name = package_name
        version = ''
    if version:
        return '%s==%s' % (name, version)
    else:
        return name


def get_mirrors(hostname=None):
    """Return the list of mirrors from the last record found on the DNS
    entry::

    >>> from pip.index import get_mirrors
    >>> get_mirrors()
    ['a.pypi.python.org', 'b.pypi.python.org', 'c.pypi.python.org',
    'd.pypi.python.org']

    Originally written for the distutils2 project by Alexis Metaireau.
    """
    if hostname is None:
        hostname = DEFAULT_MIRROR_URL

    # return the last mirror registered on PyPI.
    try:
        hostname = socket.gethostbyname_ex(hostname)[0]
    except socket.gaierror:
        return []
    end_letter = hostname.split(".", 1)

    # determine the list from the last one.
    return ["%s.%s" % (s, end_letter[1]) for s in string_range(end_letter[0])]


def string_range(last):
    """
    Compute the range of string between "a" and last.

    This works for simple "a to z" lists, but also for "a to zz" lists.
    """
    for k in range(len(last)):
        for x in product(string.ascii_lowercase, repeat=k + 1):
            result = ''.join(x)
            yield result
            if result == last:
                return


# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.
"""
Verify a DSA signature, for use with PyPI mirrors.

Verification should use the following steps:
1. Download the DSA key from http://pypi.python.org/serverkey, as key_string
2. key = load_key(key_string)
3. Download the package page, from <mirror>/simple/<package>/, as data
4. Download the package signature, from <mirror>/serversig/<package>, as sig
5. Check verify(key, data, sig)
"""

try:
    from M2Crypto import EVP, DSA, BIO

    def load_key(string):
        """
        load_key(string) -> key

        Convert a PEM format public DSA key into
        an internal representation.
        """
        return DSA.load_pub_key_bio(BIO.MemoryBuffer(string))

    def verify(key, data, sig):
        """
        verify(key, data, sig) -> bool

        Verify autenticity of the signature created by key for
        data. data is the bytes that got signed; signature is the
        bytes that represent the signature, using the sha1+DSA
        algorithm. key is an internal representation of the DSA key
        as returned from load_key."""
        md = EVP.MessageDigest('sha1')
        md.update(data)
        digest = md.final()
        return key.verify_asn1(digest, sig)

except ImportError:

    # DSA signature algorithm, taken from pycrypto 2.0.1
    # The license terms are the same as the ones for this module.
    def _inverse(u, v):
        """
        _inverse(u:long, u:long):long
        Return the inverse of u mod v.
        """
        u3, v3 = _long(u), _long(v)
        u1, v1 = _long(1), _long(0)
        while v3 > 0:
            q = u3 // v3
            u1, v1 = v1, u1 - v1 * q
            u3, v3 = v3, u3 - v3 * q
        while u1 < 0:
            u1 = u1 + v
        return u1

    def _verify(key, M, sig):
        p, q, g, y = key
        r, s = sig
        if r <= 0 or r >= q or s <= 0 or s >= q:
            return False
        w = _inverse(s, q)
        u1, u2 = (M * w) % q, (r * w) % q
        v1 = pow(g, u1, p)
        v2 = pow(y, u2, p)
        v = (v1 * v2) % p
        v = v % q
        return v == r

    # END OF pycrypto

    def _bytes2int(b):
        value = 0
        for c in b:
            value = value * 256 + ord(c)
        return value

    _SEQUENCE = 0x30  # cons
    _INTEGER = 2      # prim
    _BITSTRING = 3    # prim
    _OID = 6          # prim

    def _asn1parse(string):
        tag = ord(string[0])
        assert tag & 31 != 31  # only support one-byte tags
        length = ord(string[1])
        assert length != 128  # indefinite length not supported
        pos = 2
        if length > 128:
            # multi-byte length
            val = 0
            length -= 128
            val = _bytes2int(string[pos:pos + length])
            pos += length
            length = val
        data = string[pos:pos + length]
        rest = string[pos + length:]
        assert pos + length <= len(string)
        if tag == _SEQUENCE:
            result = []
            while data:
                value, data = _asn1parse(data)
                result.append(value)
        elif tag == _INTEGER:
            assert ord(data[0]) < 128  # negative numbers not supported
            result = 0
            for c in data:
                result = result * 256 + ord(c)
        elif tag == _BITSTRING:
            result = data
        elif tag == _OID:
            result = data
        else:
            raise ValueError("Unsupported tag %x" % tag)
        return (tag, result), rest

    def load_key(string):
        """
        load_key(string) -> key

        Convert a PEM format public DSA key into
        an internal representation."""
        lines = [line.strip() for line in string.splitlines()]
        assert lines[0] == b("-----BEGIN PUBLIC KEY-----")
        assert lines[-1] == b("-----END PUBLIC KEY-----")
        data = decode_base64(''.join([u(line) for line in lines[1:-1]]))
        spki, rest = _asn1parse(data)
        assert not rest
        # SubjectPublicKeyInfo  ::=  SEQUENCE  {
        #  algorithm            AlgorithmIdentifier,
        #  subjectPublicKey     BIT STRING  }
        assert spki[0] == _SEQUENCE
        algoid, key = spki[1]
        assert key[0] == _BITSTRING
        key = key[1]
        # AlgorithmIdentifier  ::=  SEQUENCE  {
        #  algorithm               OBJECT IDENTIFIER,
        #  parameters              ANY DEFINED BY algorithm OPTIONAL  }
        assert algoid[0] == _SEQUENCE
        algorithm, parameters = algoid[1]
        # dsaEncryption
        # assert algorithm[0] == _OID and algorithm[1] == '*\x86H\xce8\x04\x01'
        # Dss-Parms  ::=  SEQUENCE  {
        #  p             INTEGER,
        #  q             INTEGER,
        #  g             INTEGER  }
        assert parameters[0] == _SEQUENCE
        p, q, g = parameters[1]
        assert p[0] == q[0] == g[0] == _INTEGER
        p, q, g = p[1], q[1], g[1]
        # Parse bit string value as integer
        # assert key[0] == '\0'  # number of bits multiple of 8
        y, rest = _asn1parse(key[1:])
        assert not rest
        assert y[0] == _INTEGER
        y = y[1]
        return p, q, g, y

    def verify(key, data, sig):
        """
        verify(key, data, sig) -> bool

        Verify autenticity of the signature created by key for
        data. data is the bytes that got signed; signature is the
        bytes that represent the signature, using the sha1+DSA
        algorithm. key is an internal representation of the DSA key
        as returned from load_key."""
        from hashlib import sha1
        sha = sha1()
        sha.update(data)
        data = sha.digest()
        data = _bytes2int(data)
        # Dss-Sig-Value  ::=  SEQUENCE  {
        #      r       INTEGER,
        #      s       INTEGER  }
        sig, rest = _asn1parse(sig)
        assert not rest
        assert sig[0] == _SEQUENCE
        r, s = sig[1]
        assert r[0] == s[0] == _INTEGER
        sig = r[1], s[1]
        return _verify(key, data, sig)
