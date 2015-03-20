from __future__ import absolute_import

import posixpath
import re

from pip.download import path_to_url
from pip.utils import Inf, splitext
from pip._vendor.six.moves.urllib import parse as urllib_parse
from pip.wheel import wheel_ext


class Link(object):

    def __init__(self, url, comes_from=None, internal=None, trusted=None,
                 _deprecated_regex=False):

        # url can be a UNC windows share
        if url != Inf and url.startswith('\\\\'):
            url = path_to_url(url)

        self.url = url
        self.comes_from = comes_from
        self.internal = internal
        self.trusted = trusted
        self._deprecated_regex = _deprecated_regex

    def __str__(self):
        if self.comes_from:
            return '%s (from %s)' % (self.url, self.comes_from)
        else:
            return str(self.url)

    def __repr__(self):
        return '<Link %s>' % self

    def __eq__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url == other.url

    def __ne__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url != other.url

    def __lt__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url < other.url

    def __le__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url <= other.url

    def __gt__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url > other.url

    def __ge__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return self.url >= other.url

    def __hash__(self):
        return hash(self.url)

    @property
    def filename(self):
        _, netloc, path, _, _ = urllib_parse.urlsplit(self.url)
        name = posixpath.basename(path.rstrip('/')) or netloc
        name = urllib_parse.unquote(name)
        assert name, ('URL %r produced no filename' % self.url)
        return name

    @property
    def scheme(self):
        return urllib_parse.urlsplit(self.url)[0]

    @property
    def netloc(self):
        return urllib_parse.urlsplit(self.url)[1]

    @property
    def path(self):
        return urllib_parse.unquote(urllib_parse.urlsplit(self.url)[2])

    def splitext(self):
        return splitext(posixpath.basename(self.path.rstrip('/')))

    @property
    def ext(self):
        return self.splitext()[1]

    @property
    def url_without_fragment(self):
        scheme, netloc, path, query, fragment = urllib_parse.urlsplit(self.url)
        return urllib_parse.urlunsplit((scheme, netloc, path, query, None))

    _egg_fragment_re = re.compile(r'#egg=([^&]*)')

    @property
    def egg_fragment(self):
        match = self._egg_fragment_re.search(self.url)
        if not match:
            return None
        return match.group(1)

    _hash_re = re.compile(
        r'(sha1|sha224|sha384|sha256|sha512|md5)=([a-f0-9]+)'
    )

    @property
    def hash(self):
        match = self._hash_re.search(self.url)
        if match:
            return match.group(2)
        return None

    @property
    def hash_name(self):
        match = self._hash_re.search(self.url)
        if match:
            return match.group(1)
        return None

    @property
    def show_url(self):
        return posixpath.basename(self.url.split('#', 1)[0].split('?', 1)[0])

    @property
    def verifiable(self):
        """
        Returns True if this link can be verified after download, False if it
        cannot, and None if we cannot determine.
        """
        trusted = self.trusted or getattr(self.comes_from, "trusted", None)
        if trusted is not None and trusted:
            # This link came from a trusted source. It *may* be verifiable but
            #   first we need to see if this page is operating under the new
            #   API version.
            try:
                api_version = getattr(self.comes_from, "api_version", None)
                api_version = int(api_version)
            except (ValueError, TypeError):
                api_version = None

            if api_version is None or api_version <= 1:
                # This link is either trusted, or it came from a trusted,
                #   however it is not operating under the API version 2 so
                #   we can't make any claims about if it's safe or not
                return

            if self.hash:
                # This link came from a trusted source and it has a hash, so we
                #   can consider it safe.
                return True
            else:
                # This link came from a trusted source, using the new API
                #   version, and it does not have a hash. It is NOT verifiable
                return False
        elif trusted is not None:
            # This link came from an untrusted source and we cannot trust it
            return False

    @property
    def is_wheel(self):
        return self.ext == wheel_ext


# An object to represent the "link" for the installed version of a requirement.
# Using Inf as the url makes it sort higher.
INSTALLED_VERSION = Link(Inf)
