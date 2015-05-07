from __future__ import absolute_import

from collections import defaultdict
import logging
import os.path
import shutil
import tempfile
import zipfile

from pip._vendor import pkg_resources
from pip._vendor import requests

import pip
from pip.download import (url_to_path, unpack_url)
from pip.exceptions import DistributionNotFound, InstallationError
from pip.utils import (
    ask_path_exists, backup_dir, display_path, ensure_dir, rmtree,
    _make_build_dir)
from pip.locations import PIP_DELETE_MARKER_FILENAME
from pip.utils.logging import indent_log


logger = logging.getLogger(__name__)


class RequirementCache(object):
    """A cache of requirements.

    This is responsible for maintaining global state independent of resolver
    state. E.g. what versions of a package the index has, or the path on disk
    of an unpacked copy of version X.

    This separation enables reuse of cached resources in multiple resolver
    runs e.g. the top level install, and then per-setup-requires resolution.

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

    def __init__(self, path=None, delete=None, src_dir=None, finder=None,
                 isolated=False, wheel_cache=None):
        """Create a RequirementCache.

        :param path: The path to store working data - wheels, sdists, etc. If
            None then a temp dir will be made on __enter__.
        :param delete: If False then path will not be deleted on __exit__.
            If None, then path will be deleted on __exit__ only if path was
            None. If True then path will be deleted on __exit__.
        :param src_dir: The parent path that editable non-local requirements
            will be checked out under. Will be created on demand if needed.
        :param finder: The finder to use to obtain package lists.
        :param isolated: Is the install being isolated.
        :param wheel_cache: Optional lookaside cache for auto-built wheels.
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
        self._finder = finder
        self.isolated = isolated
        self.wheel_cache = wheel_cache

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
        ensure_dir(self.download_dir)
        self._urls = {}  # type: Dict[str, CachedRequirement]
        self._names = defaultdict(dict)
        # type: Dict[str, Dict[str, CachedRequirement]]
        self._versions = {}  # type: Dict[str, [[str], [InstallationCandidate]
        self._reqs = set()  # type: Set[CachedRequirement]
        self._requires = {}
        # type: Dict[[str, tuple(extras), version], [[str, tuple[extras],
        # Specifier]
        self._installed = {}  # type: Dict[str, Distribution]
        return self

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.delete:
            logger.debug('Cleaning up...')
            rmtree(self.path)
        self.path = None
        self._urls = None
        self._names = None
        self._reqs = None
        self._versions = None
        self._requires = None

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
        if req.editable and not req.url.url.startswith('file://'):
            assert self.src_dir
            if not req.name:
                raise ValueError(req)
        assert self._urls is not None
        if req in self._reqs:
            raise ValueError(req)
        if req.url:
            if req.url.url in self._urls:
                raise ValueError(req)
            self._urls[req.url.url] = req
        if req.name:
            if req.version:
                if req.version in self._names[req.name]:
                    raise ValueError(req)
                self._names[req.name][req.version] = req
            elif not req.url:
                # Either name + URL or name + version: there's no support for
                # name and nothing else as a CachedRequirement:
                # CachedRequirements have been resolved.
                raise ValueError(req)
        self._reqs.add(req)

    @property
    def download_dir(self):
        """Temporary location to download archives to while we resolve.

        Once resolution is complete the selected archives can be copied to the
        users download dir.
        """
        return os.path.join(self.path, 'download')

    def build_path(self, req):
        """Assert the build path for req.

        This is:
         - the local url for editable file:/// requirements that point to
           source dirs.
         - self.src_dir + / + req.name for editable non-file:/// requirements
           - these require the name to be set in
             InstallRequirement.from_editable.
         - a temporary path in self.path for all other requirements.

        The build path is calculated once only for a req and cached on the
        req object as build_path.

        The first time this is called for a req a directory is ensured. For
        non editable requirements the whole build path is created, and for
        editable requirements the parent directory of the build path is
        created.
        """
        if req not in self._reqs:
            raise KeyError(req)
        if req.build_path:
            return req.build_path
        if req.editable and req.url.url.startswith('file:'):
            build_path = url_to_path(req.url.url)
        elif req.editable:
            assert req.name
            build_path = os.path.join(self.src_dir, req.name)
        else:
            build_path = tempfile.mkdtemp('-build', 'pip-', self.path)
        if req.editable:
            ensure_dir(os.path.dirname(build_path))
        req.build_path = build_path
        return req.build_path

    def candidate_from_version(self, name, version):
        """Get the candidate for version of name.

        :param name: The name.
        :param version: The version that was selected.
        :return: The InstallationCandidate.
        """
        canonical_name = pkg_resources.safe_name(name).lower()
        _, all_versions = self._versions[canonical_name]
        for candidate in all_versions:
            if candidate.version == version:
                return candidate
        raise KeyError("version not found %s %s" % (name, version))

    def get_versions(self, name, upgrade, permit_installed):
        """Get all the versions of name.

        :param name: A requirement name.
        :param upgrade: If False, the current installed version will be
            placed first in the result.
        :param permit_installed: If False, don't consult local package metadata
            for dependency information - used when doing a forced
            reinstallation.
        :return: A tuple of Version objects, sorted in preference order.
        """
        canonical_name = pkg_resources.safe_name(name).lower()
        if canonical_name in self._versions:
            return self._versions[canonical_name][0]
        all_versions = self._finder._find_all_versions(name)
        if permit_installed:
            try:
                installed_version = pkg_resources.get_distribution(name)
                inst_key = "%s-%s" % (canonical_name, installed_version.version)
                self._installed[inst_key] = installed_version
                installed_candidate= pip.index.InstallationCandidate(
                    name, installed_version.version, pip.index.INSTALLED_VERSION)
            except pkg_resources.DistributionNotFound:
                installed_version = None
        if permit_installed and installed_version and upgrade:
            # For upgrades, the installed version is one amongst many.
            all_versions.append(installed_candidate)
        all_versions = self._finder._sort_versions(all_versions)
        if permit_installed and installed_version and not upgrade:
            # For as-needed upgrades, the installed version is the first one to
            # consider.
            all_versions.insert(0, installed_candidate)
        self._set_all_versions(canonical_name, all_versions)
        # XXX: TODO: finder warnings?
        if not all_versions:
            raise DistributionNotFound("No distribution found for %s" % name)
        return self._versions[canonical_name][0]

    def guess_scale(self):
        """Guess at how big a problem we're facing."""
        scale = 1.0
        all_versions = 0
        for versions, _ in self._versions.values():
            scale *= len(versions)
            all_versions += len(versions)
        return scale, all_versions, len(self._versions)

    def installed(self, name, version):
        """Return True if name has version version isntalled."""
        canonical_name = pkg_resources.safe_name(name).lower()
        inst_key = "%s-%s" % (canonical_name, version)
        return inst_key in self._installed

    def lock_version(self, cached_req):
        """Make this version the only version of cached_req.name available.

        :param cached_req: A named CachedRequirement already present in the
            cache.
        """
        candidate = self.candidate_from_version(
            cached_req.name, cached_req.version)
        canonical_name = pkg_resources.safe_name(cached_req.name).lower()
        self._versions[canonical_name] = ((candidate.version,), [candidate])
        # We *don't* alter self._installed: thats queried only when installing
        # and for location requirements we want to always uninstall and
        # reinstall.

    def lookup_url(self, url):
        """Lookup a requirement.

        :param url: The URL to the requirement. Used for both VCS (e.g. git+)
            URLs, and local directories (file://...) urls that point
            at source trees.
        :raises: KeyError if there is no matching requirement
        :return: The CachedRequirement object if found.
        """
        return self._urls[url.url]

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

    def _dist_to_requires(self, key, dist, extras):
        missing_requested = sorted(set(extras) - set(dist.extras))
        for missing in missing_requested:
            logger.warning(
                '%s does not provide the extra \'%s\'', dist, missing)
        available_requested = sorted(set(dist.extras) & set(extras))
        requires = []
        for req in dist.requires(available_requested):
            req_name = pkg_resources.safe_name(req.project_name).lower()
            requires.append(
                (req_name, tuple(sorted(req.extras)), req.specifier))
        requires = tuple(requires)
        self._requires[key] = requires
        logger.debug('Cached requires for %s %s' % (key, requires))
        return requires

    def requires(self, name, extras, version, permit_installed):
        """Get the requirements for a version of name.

        :param name: The package name being looked up.
        :param extras: The extras being requested.
        :param version: The version being requested.
        :param permit_installed: If False, don't consult local package metadata
            for dependency information - used when doing a forced
            reinstallation.
        :return: An iterable of (name, extras, specifier).
        """
        key = (name, extras, version)
        if key in self._requires:
            result = self._requires[key]
            if type(result) is not InstallationError:
                return result
            else:
                raise result
        canonical_name = pkg_resources.safe_name(name).lower()
        # Installed? Local is cheap
        dist = self._installed.get("%s-%s" % (canonical_name, version), None)
        if permit_installed and dist:
            # XXX: For installed editable reqs we should probably re-evaluate
            # them once during upgrades: requires marking them as such in
            # get_versions.
            return self._dist_to_requires(key, dist, extras)
        # Network / files etc
        try:
            cached_req = self.lookup_name(canonical_name, version)
        except KeyError:
            # Hasn't been pulled down yet.
            cached_req = CachedRequirement(
                name=canonical_name, version=version)
            self.add(cached_req)
        try:
            dist = cached_req.dist(self)
        except InstallationError as e:
            # We failed to build egg_info data for this distribution,
            self._requires[key] = e
            # Should clear frames on e? Not sure how common this is.
            logger.debug(
                "Could not build egg_info for %s(%s).", name, version)
            raise
        if (pkg_resources.safe_name(dist.project_name).lower() !=
                canonical_name) or (pkg_resources.parse_version(
                dist.version) != version):
            msg = ("Discovered version %s of %s but archive contains %s" %
                   (version, name, dist.version))
            logger.warning(msg)
            # raise InstallationError(msg)

        # FIXME: shouldn't be globally added:
        if dist.has_metadata('dependency_links.txt'):
            self._finder.add_dependency_links(
                dist.get_metadata_lines('dependency_links.txt')
            )
        return self._dist_to_requires(key, dist, extras)

    def _set_all_versions(self, canonical_name, all_versions):
        just_versions = []
        versions_set = set()
        for candidate in all_versions:
            if candidate.version not in versions_set:
                just_versions.append(candidate.version)
                versions_set.add(candidate.version)
        self._versions[canonical_name] = (
            tuple(just_versions), all_versions)

    def update_name(self, cached_req, name, version):
        """Update the name of a location based requirement.

        :param cached_req: The cached requirement to update.
        :param name: The name to give it.
        :param version: The version to give it.
        """
        assert self.lookup_url(cached_req.url) is cached_req
        canonical_name = pkg_resources.safe_name(name).lower()
        cached_req.name = canonical_name
        version = pkg_resources.parse_version(version)
        cached_req.version = version
        # Basic mapping - move from URL to name.
        self._urls.pop(cached_req.url.url)
        self._names[canonical_name][cached_req.version] = cached_req
        # Put this version into the known versions.
        candidate = pip.index.InstallationCandidate(
            name, str(version), cached_req.url)
        if canonical_name not in self._versions:
            # This name has not been queried yet.
            self._versions[canonical_name] = ((), [])
        _, all_versions = self._versions[canonical_name]
        # At the front so that its the first consulted.
        all_versions.insert(0, candidate)
        self._set_all_versions(canonical_name, all_versions)


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
    :attr build_path: The path where the requirement is being built.
    :attr candidate: None or an InstallationCandidate for this requirement.
    """

    def __init__(self, name=None, version=None, url=None, editable=False,
                 editable_options=None):
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
        :param editable_options: Options controlling editable behaviour.

        To be cachable a requirement must be either be specific - e.g. name
        and exact version, or have a url.
        """
        self.url = url
        self.name = name
        assert type(version) is not str  # XXX debug code
        self.version = version
        self.editable = editable
        self.build_path = None
        self.candidate = None
        self._abstract_dist = None
        self._dist = None
        self._editable_options = editable_options or {}

    def archive(self, output_dir):
        """Archive this source tree somewhere.

        :param output_dir: Where to archive it.
        """
        # Must know the package name and version to archive it.
        assert self._dist
        assert self.name
        assert self.version
        create_archive = True
        archive_name = '%s-%s.zip' % (self.name, self.version)
        archive_path = os.path.join(output_dir, archive_name)
        if os.path.exists(archive_path):
            response = ask_path_exists(
                'The file %s exists. (i)gnore, (w)ipe, (b)ackup ' %
                display_path(archive_path), ('i', 'w', 'b'))
            if response == 'i':
                create_archive = False
            elif response == 'w':
                logger.warning('Deleting %s', display_path(archive_path))
                os.remove(archive_path)
            elif response == 'b':
                dest_file = backup_dir(archive_path)
                logger.warning(
                    'Backing up %s to %s',
                    display_path(archive_path),
                    display_path(dest_file),
                )
                shutil.move(archive_path, dest_file)
        if create_archive:
            zip = zipfile.ZipFile(
                archive_path, 'w', zipfile.ZIP_DEFLATED,
                allowZip64=True
            )
            dir = os.path.normcase(os.path.abspath(self.build_path))
            for dirpath, dirnames, filenames in os.walk(dir):
                if 'pip-egg-info' in dirnames:
                    dirnames.remove('pip-egg-info')
                for dirname in dirnames:
                    dirname = os.path.join(dirpath, dirname)
                    name = self._clean_zip_name(dirname, dir)
                    zipdir = zipfile.ZipInfo(self.name + '/' + name + '/')
                    zipdir.external_attr = 0x1ED << 16  # 0o755
                    zip.writestr(zipdir, '')
                for filename in filenames:
                    if filename == PIP_DELETE_MARKER_FILENAME:
                        continue
                    filename = os.path.join(dirpath, filename)
                    name = self._clean_zip_name(filename, dir)
                    zip.write(filename, self.name + '/' + name)
            zip.close()
            logger.info('Saved %s', display_path(archive_path))

    def _clean_zip_name(self, name, prefix):
        assert name.startswith(prefix + os.path.sep), (
            "name %r doesn't start with prefix %r" % (name, prefix)
        )
        name = name[len(prefix) + 1:]
        name = name.replace(os.path.sep, '/')
        return name

    def dist(self, req_cache):
        """Get a Distribution object for this CachedRequirement.

        :param req_cache: The cache.
        """
        if self._dist is not None:
            return self._dist
        if self._abstract_dist is None:
            link = self._unpack(req_cache)
            self._abstract_dist = self._inspect_disk(link)
        self._dist = self._abstract_dist.dist(req_cache)
        return self._dist

    def _unpack(self, req_cache):
        """Download and unpack into the cache.

        :param req_cache: The cache.
        """
        if self.name is not None:
            assert req_cache.lookup_name(self.name, self.version) is self
        else:
            assert False
            assert req_cache.lookup_url(self.url) is self
        candidate = req_cache.candidate_from_version(self.name, self.version)
        self.candidate = candidate
        link = candidate.location
        if req_cache.wheel_cache:
            link = req_cache.wheel_cache.cached_wheel(link, self.name)
        autodelete_unpacked = not link.is_wheel
        try:
            unpack_url(
                link, req_cache.build_path(self), req_cache.download_dir,
                autodelete_unpacked, session=req_cache._finder.session)
        except requests.HTTPError as exc:
            logger.critical(
                'Could not install requirement %s because '
                'of error %s', self, exc,)
            raise InstallationError(
                'Could not install requirement %s because '
                'of HTTP error %s for URL %s' % (self, exc, link))
        return link

    def _inspect_disk(self, link):
        if link.is_wheel:
            return pip.req.req_install._IsWheel(self.build_path)
        return pip.req.req_install._IsSDist(
            self.build_path, self._editable_options, self.editable)
