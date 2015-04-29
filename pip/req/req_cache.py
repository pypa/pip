from __future__ import absolute_import

from collections import defaultdict
import os.path
import tempfile

from pip.utils import rmtree


class RequirementCache(object):
    """A cache of requirements.

    :attr delete: May be set to False to disable deleting the cache.

    Design
    ------

    The cache is responsible for holding requirements - be those local paths,
    tarballs, VCS repositories or package names. The constraints placed on
    selection of requirements are handled by the RequirementSet, and must not
    be pushed down into the cache - because the cache will return the same
    requirement each time it is referenced. InstallRequirement is being
    broken into the cachable component (CachedRequirement) and the uncachable
    per-evaluation component (InstallRequirement).

    RequirementCache owns CachedRequirements, so the primary interface is
    to ask the cache to perform an operation when cache state is needed.
    """

    def __init__(self, path=None, delete=None, src_dir=None):
        """Create a RequirementCache.

        :param path: The path to store working data - wheels, sdists, etc. If
            None then a temp dir will be made on __enter__.
        :param delete: If False then path will not be deleted on __exit__.
            If None, then path will be deleted on __exit__ only if path was
            None. If True then path will be deleted on __exit__.
        :param src_dir: The parent path that editable non-local requirements
            will be checked out under. Will be created on demand if needed.
        """
        # If we were not given an explicit directory, and we were not given an
        # explicit delete option, then we'll default to deleting.
        if path is None and delete is None:
            delete = True
        self._path = path

        self.path = None
        self.delete = delete
        self.src_dir = os.path.abspath(src_dir) if src_dir else None
        self._urls = None

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.path)

    def __enter__(self):
        if self._path is None:
            # We realpath here because some systems have their default tmpdir
            # symlinked to another directory.  This tends to confuse build
            # scripts, so we canonicalize the path by traversing potential
            # symlinks here.
            self.path = os.path.realpath(tempfile.mkdtemp(prefix="pip-build-"))
            # If we were not given an explicit directory, and we were not given
            # an explicit delete option, then we'll default to deleting.
            if self.delete is None:
                self.delete = True
        else:
            self.path = self._path
        self._urls = {}  # type: Dict[str, CachedRequirement]
        self._names = defaultdict(dict) # type: Dict[str, Dict[str, CachedRequirement]]
        return self

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.delete:
            rmtree(self.path)
        self.path = None
        self._urls = None
        self._names = None

    def add(self, req):
        """Allocate a slot for req in the cache.

        There are three sorts of slots:
         - external sources - e.g. /my/path/to/a/tree
         - downloaded editable sources - downloaded to self.src_dir/name
         - everything else - downloaded to a temporary directory in self.path,
            with the req name as a prefix when its known.

        We cannot determine the version of the first two forms of requirement
        until their setup-requirements are also available, thus the cache has
        two different keys - path|url, and (name, version) tuples.

        :param req: a CachedRequirement.
        """
        if req.editable and not req.url.startswith('file://'):
            assert self.src_dir
        assert self._urls is not None
        if req.url:
            if req.url in self._urls:
                raise ValueError(req)
            self._urls[req.url] = req
        if req.name and req.version:
            if req.version in self._names[req.name]:
                raise ValueError(req)
            self._names[req.name][req.version] = req


    def lookup_url(self, url):
        """Lookup a requirement.

        :param url: The URL to the requirement. Used for both VCS (e.g. git+)
            URLs, and local directories (file://...) urls that point
            at source trees.
        :raises: KeyError if there is no matching requirement
        :return: The CachedRequirement object if found.
        """
        return self._urls[url]

    def lookup_name(self, name, version):
        """Lookup a requirement.

        :param name: The name of the requirement.
        :param version: The version of the requirement.
        :raises: KeyError if there is no matching requirement
        :return: The CachedRequirement object if found.
        """
        try:
            return self._names[name][version]
        except KeyError:
            raise KeyError("%s-%s" % (name, version))


class CachedRequirement(object):
    """Cacheable component of InstallRequirement.

    :attr url: The URL for the requirement, if it was specified as a URL or
        path.
    :attr name: The canonical name of the requirement or None if it is not yet
        known (which is for requirements specifiied by URL).
    :attr version: The version of the requirement or None if it is not yet
        known (also for URL specified requirements).
    :attr editable: The editability of a requirement affects the directory
        that will be used.
    """

    def __init__(self, name=None, version=None, url=None, editable=False):
        """Create a CachedRequirement.

        :param name: The name of the requirement. None if it is not known.
            The name should be passed in in canonical form.
        :param version: The version of the requirement. None if it not known.
        :param url: The url to the requirement. Used for both local source
            trees and arbitrary urls.
        :param editable: Is the requirement going to be updated over time -
            as an editable install. This affects both the directory (the cache
            src_dir is used, which persists) and the way the intallation is
            accomplished).

        To be cachable a requirement must be either be specific - e.g. name
        and exact version, or have a url.
        """
        self.url = url
        self.name = name
        self.version = version
        self.editable = editable
