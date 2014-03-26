import os
import shutil
import zipfile

from pip._vendor import pkg_resources
from pip.backwardcompat import HTTPError
from pip.download import (PipSession, url_to_path, unpack_vcs_link, is_vcs_url,
                          is_file_url, unpack_file_url, unpack_http_url)
from pip.exceptions import (InstallationError, BestVersionAlreadyInstalled,
                            DistributionNotFound, PreviousBuildDirError)
from pip.index import Link
from pip.locations import (PIP_DELETE_MARKER_FILENAME, build_prefix,
                           write_delete_marker_file)
from pip.log import logger
from pip.req.req_install import InstallRequirement
from pip.util import (display_path, rmtree, dist_in_usersite, call_subprocess,
                      _make_build_dir)
from pip.vcs import vcs
from pip.wheel import wheel_ext


class Requirements(object):

    def __init__(self):
        self._keys = []
        self._dict = {}

    def keys(self):
        return self._keys

    def values(self):
        return [self._dict[key] for key in self._keys]

    def __contains__(self, item):
        return item in self._keys

    def __setitem__(self, key, value):
        if key not in self._keys:
            self._keys.append(key)
        self._dict[key] = value

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        values = ['%s: %s' % (repr(k), repr(self[k])) for k in self.keys()]
        return 'Requirements({%s})' % ', '.join(values)


class RequirementSet(object):

    def __init__(self, build_dir, src_dir, download_dir, download_cache=None,
                 upgrade=False, ignore_installed=False, as_egg=False,
                 target_dir=None, ignore_dependencies=False,
                 force_reinstall=False, use_user_site=False, session=None,
                 pycompile=True, wheel_download_dir=None):
        self.build_dir = build_dir
        self.src_dir = src_dir
        self.download_dir = download_dir
        if download_cache:
            download_cache = os.path.expanduser(download_cache)
        self.download_cache = download_cache
        self.upgrade = upgrade
        self.ignore_installed = ignore_installed
        self.force_reinstall = force_reinstall
        self.requirements = Requirements()
        # Mapping of alias: real_name
        self.requirement_aliases = {}
        self.unnamed_requirements = []
        self.ignore_dependencies = ignore_dependencies
        self.successfully_downloaded = []
        self.successfully_installed = []
        self.reqs_to_cleanup = []
        self.as_egg = as_egg
        self.use_user_site = use_user_site
        self.target_dir = target_dir  # set from --target option
        self.session = session or PipSession()
        self.pycompile = pycompile
        self.wheel_download_dir = wheel_download_dir

    def __str__(self):
        reqs = [req for req in self.requirements.values()
                if not req.comes_from]
        reqs.sort(key=lambda req: req.name.lower())
        return ' '.join([str(req.req) for req in reqs])

    def add_requirement(self, install_req):
        name = install_req.name
        install_req.as_egg = self.as_egg
        install_req.use_user_site = self.use_user_site
        install_req.target_dir = self.target_dir
        install_req.pycompile = self.pycompile
        if not name:
            # url or path requirement w/o an egg fragment
            self.unnamed_requirements.append(install_req)
        else:
            if self.has_requirement(name):
                raise InstallationError(
                    'Double requirement given: %s (already in %s, name=%r)'
                    % (install_req, self.get_requirement(name), name))
            self.requirements[name] = install_req
            # FIXME: what about other normalizations?  E.g., _ vs. -?
            if name.lower() != name:
                self.requirement_aliases[name.lower()] = name

    def has_requirement(self, project_name):
        for name in project_name, project_name.lower():
            if name in self.requirements or name in self.requirement_aliases:
                return True
        return False

    @property
    def has_requirements(self):
        return list(self.requirements.values()) or self.unnamed_requirements

    @property
    def has_editables(self):
        if any(req.editable for req in self.requirements.values()):
            return True
        if any(req.editable for req in self.unnamed_requirements):
            return True
        return False

    @property
    def is_download(self):
        if self.download_dir:
            self.download_dir = os.path.expanduser(self.download_dir)
            if os.path.exists(self.download_dir):
                return True
            else:
                logger.fatal('Could not find download directory')
                raise InstallationError(
                    "Could not find or access download directory '%s'"
                    % display_path(self.download_dir))
        return False

    def get_requirement(self, project_name):
        for name in project_name, project_name.lower():
            if name in self.requirements:
                return self.requirements[name]
            if name in self.requirement_aliases:
                return self.requirements[self.requirement_aliases[name]]
        raise KeyError("No project with the name %r" % project_name)

    def uninstall(self, auto_confirm=False):
        for req in self.requirements.values():
            req.uninstall(auto_confirm=auto_confirm)
            req.commit_uninstall()

    def locate_files(self):
        # FIXME: duplicates code from prepare_files; relevant code should
        #        probably be factored out into a separate method
        unnamed = list(self.unnamed_requirements)
        reqs = list(self.requirements.values())
        while reqs or unnamed:
            if unnamed:
                req_to_install = unnamed.pop(0)
            else:
                req_to_install = reqs.pop(0)
            install_needed = True
            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()
                if req_to_install.satisfied_by:
                    if self.upgrade:
                        # don't uninstall conflict if user install and and
                        # conflict is not user install
                        if not (self.use_user_site
                                and not dist_in_usersite(
                                    req_to_install.satisfied_by
                                )):
                            req_to_install.conflicts_with = \
                                req_to_install.satisfied_by
                        req_to_install.satisfied_by = None
                    else:
                        install_needed = False
                if req_to_install.satisfied_by:
                    logger.notify('Requirement already satisfied '
                                  '(use --upgrade to upgrade): %s'
                                  % req_to_install)

            if req_to_install.editable:
                if req_to_install.source_dir is None:
                    req_to_install.source_dir = req_to_install.build_location(
                        self.src_dir
                    )
            elif install_needed:
                req_to_install.source_dir = req_to_install.build_location(
                    self.build_dir,
                    not self.is_download,
                )

            if (req_to_install.source_dir is not None
                    and not os.path.isdir(req_to_install.source_dir)):
                raise InstallationError(
                    'Could not install requirement %s because source folder %s'
                    ' does not exist (perhaps --no-download was used without '
                    'first running an equivalent install with --no-install?)' %
                    (req_to_install, req_to_install.source_dir)
                )

    def prepare_files(self, finder, force_root_egg_info=False, bundle=False):
        """
        Prepare process. Create temp directories, download and/or unpack files.
        """
        unnamed = list(self.unnamed_requirements)
        reqs = list(self.requirements.values())
        while reqs or unnamed:
            if unnamed:
                req_to_install = unnamed.pop(0)
            else:
                req_to_install = reqs.pop(0)
            install = True
            best_installed = False
            not_found = None

            # ############################################# #
            # # Search for archive to fulfill requirement # #
            # ############################################# #

            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()
                if req_to_install.satisfied_by:
                    if self.upgrade:
                        if not self.force_reinstall and not req_to_install.url:
                            try:
                                url = finder.find_requirement(
                                    req_to_install, self.upgrade)
                            except BestVersionAlreadyInstalled:
                                best_installed = True
                                install = False
                            except DistributionNotFound as exc:
                                not_found = exc
                            else:
                                # Avoid the need to call find_requirement again
                                req_to_install.url = url.url

                        if not best_installed:
                            # don't uninstall conflict if user install and
                            # conflict is not user install
                            if not (self.use_user_site
                                    and not dist_in_usersite(
                                        req_to_install.satisfied_by
                                    )):
                                req_to_install.conflicts_with = \
                                    req_to_install.satisfied_by
                            req_to_install.satisfied_by = None
                    else:
                        install = False
                if req_to_install.satisfied_by:
                    if best_installed:
                        logger.notify('Requirement already up-to-date: %s'
                                      % req_to_install)
                    else:
                        logger.notify('Requirement already satisfied '
                                      '(use --upgrade to upgrade): %s'
                                      % req_to_install)
            if req_to_install.editable:
                logger.notify('Obtaining %s' % req_to_install)
            elif install:
                if (req_to_install.url
                        and req_to_install.url.lower().startswith('file:')):
                    logger.notify(
                        'Unpacking %s' %
                        display_path(url_to_path(req_to_install.url))
                    )
                else:
                    logger.notify('Downloading/unpacking %s' % req_to_install)
            logger.indent += 2

            # ################################ #
            # # vcs update or unpack archive # #
            # ################################ #

            try:
                is_bundle = False
                is_wheel = False
                if req_to_install.editable:
                    if req_to_install.source_dir is None:
                        location = req_to_install.build_location(self.src_dir)
                        req_to_install.source_dir = location
                    else:
                        location = req_to_install.source_dir
                    if not os.path.exists(self.build_dir):
                        _make_build_dir(self.build_dir)
                    req_to_install.update_editable(not self.is_download)
                    if self.is_download:
                        req_to_install.run_egg_info()
                        req_to_install.archive(self.download_dir)
                    else:
                        req_to_install.run_egg_info()
                elif install:
                    # @@ if filesystem packages are not marked
                    # editable in a req, a non deterministic error
                    # occurs when the script attempts to unpack the
                    # build directory

                    # NB: This call can result in the creation of a temporary
                    # build directory
                    location = req_to_install.build_location(
                        self.build_dir,
                        not self.is_download,
                    )
                    unpack = True
                    url = None

                    # In the case where the req comes from a bundle, we should
                    # assume a build dir exists and move on
                    if req_to_install.from_bundle:
                        pass
                    # If a checkout exists, it's unwise to keep going.  version
                    # inconsistencies are logged later, but do not fail the
                    # installation.
                    elif os.path.exists(os.path.join(location, 'setup.py')):
                        raise PreviousBuildDirError(
                            "pip can't proceed with requirements '%s' due to a"
                            " pre-existing buld directory (%s). This is likely"
                            " due to a previous installation that failed. pip "
                            "is being responsible and not assuming it can "
                            "delete this. Please delete it and try again." %
                            (req_to_install, location)
                        )
                    else:
                        # FIXME: this won't upgrade when there's an existing
                        # package unpacked in `location`
                        if req_to_install.url is None:
                            if not_found:
                                raise not_found
                            url = finder.find_requirement(
                                req_to_install,
                                upgrade=self.upgrade,
                            )
                        else:
                            # FIXME: should req_to_install.url already be a
                            # link?
                            url = Link(req_to_install.url)
                            assert url
                        if url:
                            try:

                                if (
                                    url.filename.endswith(wheel_ext)
                                    and self.wheel_download_dir
                                ):
                                    # when doing 'pip wheel`
                                    download_dir = self.wheel_download_dir
                                    do_download = True
                                else:
                                    download_dir = self.download_dir
                                    do_download = self.is_download
                                self.unpack_url(
                                    url, location, download_dir,
                                    do_download,
                                )
                            except HTTPError as exc:
                                logger.fatal(
                                    'Could not install requirement %s because '
                                    'of error %s' % (req_to_install, exc)
                                )
                                raise InstallationError(
                                    'Could not install requirement %s because '
                                    'of HTTP error %s for URL %s' %
                                    (req_to_install, exc, url)
                                )
                        else:
                            unpack = False
                    if unpack:
                        is_bundle = req_to_install.is_bundle
                        is_wheel = url and url.filename.endswith(wheel_ext)
                        if is_bundle:
                            req_to_install.move_bundle_files(
                                self.build_dir,
                                self.src_dir,
                            )
                            for subreq in req_to_install.bundle_requirements():
                                reqs.append(subreq)
                                self.add_requirement(subreq)
                        elif self.is_download:
                            req_to_install.source_dir = location
                            if not is_wheel:
                                # FIXME:https://github.com/pypa/pip/issues/1112
                                req_to_install.run_egg_info()
                            if url and url.scheme in vcs.all_schemes:
                                req_to_install.archive(self.download_dir)
                        elif is_wheel:
                            req_to_install.source_dir = location
                            req_to_install.url = url.url
                        else:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if force_root_egg_info:
                                # We need to run this to make sure that the
                                # .egg-info/ directory is created for packing
                                # in the bundle
                                req_to_install.run_egg_info(
                                    force_root_egg_info=True,
                                )
                            req_to_install.assert_source_matches_version()
                            # @@ sketchy way of identifying packages not
                            # grabbed from an index
                            if bundle and req_to_install.url:
                                self.copy_to_build_dir(req_to_install)
                                install = False
                        # req_to_install.req is only avail after unpack for URL
                        # pkgs repeat check_if_exists to uninstall-on-upgrade
                        # (#14)
                        if not self.ignore_installed:
                            req_to_install.check_if_exists()
                        if req_to_install.satisfied_by:
                            if self.upgrade or self.ignore_installed:
                                # don't uninstall conflict if user install and
                                # conflict is not user install
                                if not (self.use_user_site
                                        and not dist_in_usersite(
                                            req_to_install.satisfied_by)):
                                    req_to_install.conflicts_with = \
                                        req_to_install.satisfied_by
                                req_to_install.satisfied_by = None
                            else:
                                logger.notify(
                                    'Requirement already satisfied (use '
                                    '--upgrade to upgrade): %s' %
                                    req_to_install
                                )
                                install = False

                # ###################### #
                # # parse dependencies # #
                # ###################### #

                if is_wheel:
                    dist = list(
                        pkg_resources.find_distributions(location)
                    )[0]
                    if not req_to_install.req:
                        req_to_install.req = dist.as_requirement()
                        self.add_requirement(req_to_install)
                    if not self.ignore_dependencies:
                        for subreq in dist.requires(
                                req_to_install.extras):
                            if self.has_requirement(
                                    subreq.project_name):
                                continue
                            subreq = InstallRequirement(str(subreq),
                                                        req_to_install)
                            reqs.append(subreq)
                            self.add_requirement(subreq)

                # sdists
                elif not is_bundle:
                    if (req_to_install.extras):
                        logger.notify(
                            "Installing extra requirements: %r" %
                            ','.join(req_to_install.extras)
                        )
                    if not self.ignore_dependencies:
                        for req in req_to_install.requirements(
                                req_to_install.extras):
                            try:
                                name = pkg_resources.Requirement.parse(
                                    req
                                ).project_name
                            except ValueError as exc:
                                # FIXME: proper warning
                                logger.error(
                                    'Invalid requirement: %r (%s) in '
                                    'requirement %s' %
                                    (req, exc, req_to_install)
                                )
                                continue
                            if self.has_requirement(name):
                                # FIXME: check for conflict
                                continue
                            subreq = InstallRequirement(req, req_to_install)
                            reqs.append(subreq)
                            self.add_requirement(subreq)
                    if not self.has_requirement(req_to_install.name):
                        # 'unnamed' requirements will get added here
                        self.add_requirement(req_to_install)

                # cleanup tmp src
                if not is_bundle:
                    if (
                        self.is_download or
                        req_to_install._temp_build_dir is not None
                    ):
                        self.reqs_to_cleanup.append(req_to_install)
                if install:
                    self.successfully_downloaded.append(req_to_install)
                    if (bundle
                            and (
                                req_to_install.url
                                and req_to_install.url.startswith('file:///')
                            )):
                        self.copy_to_build_dir(req_to_install)
            finally:
                logger.indent -= 2

    def cleanup_files(self, bundle=False):
        """Clean up files, remove builds."""
        logger.notify('Cleaning up...')
        logger.indent += 2
        for req in self.reqs_to_cleanup:
            req.remove_temporary_source()

        remove_dir = []
        if self._pip_has_created_build_dir():
            remove_dir.append(self.build_dir)

        # The source dir of a bundle can always be removed.
        # FIXME: not if it pre-existed the bundle!
        if bundle:
            remove_dir.append(self.src_dir)

        for dir in remove_dir:
            if os.path.exists(dir):
                logger.info('Removing temporary dir %s...' % dir)
                rmtree(dir)

        logger.indent -= 2

    def _pip_has_created_build_dir(self):
        return (
            self.build_dir == build_prefix
            and os.path.exists(
                os.path.join(self.build_dir, PIP_DELETE_MARKER_FILENAME)
            )
        )

    def copy_to_build_dir(self, req_to_install):
        target_dir = req_to_install.editable and self.src_dir or self.build_dir
        logger.info("Copying %s to %s" % (req_to_install.name, target_dir))
        dest = os.path.join(target_dir, req_to_install.name)
        shutil.copytree(req_to_install.source_dir, dest)
        call_subprocess(["python", "%s/setup.py" % dest, "clean"], cwd=dest,
                        command_desc='python setup.py clean')

    def unpack_url(self, link, location, download_dir=None,
                   only_download=False):
        if download_dir is None:
            download_dir = self.download_dir

        # non-editable vcs urls
        if is_vcs_url(link):
            if only_download:
                loc = download_dir
            else:
                loc = location
            unpack_vcs_link(link, loc, only_download)

        # file urls
        elif is_file_url(link):
            unpack_file_url(link, location, download_dir)
            if only_download:
                write_delete_marker_file(location)

        # http urls
        else:
            unpack_http_url(
                link,
                location,
                self.download_cache,
                download_dir,
                self.session,
            )
            if only_download:
                write_delete_marker_file(location)

    def install(self, install_options, global_options=(), *args, **kwargs):
        """
        Install everything in this set (after having downloaded and unpacked
        the packages)
        """
        to_install = [r for r in self.requirements.values()
                      if not r.satisfied_by]

        # DISTRIBUTE TO SETUPTOOLS UPGRADE HACK (1 of 3 parts)
        # move the distribute-0.7.X wrapper to the end because it does not
        # install a setuptools package. by moving it to the end, we ensure it's
        # setuptools dependency is handled first, which will provide the
        # setuptools package
        # TODO: take this out later
        distribute_req = pkg_resources.Requirement.parse("distribute>=0.7")
        for req in to_install:
            if (req.name == 'distribute'
                    and req.installed_version in distribute_req):
                to_install.remove(req)
                to_install.append(req)

        if to_install:
            logger.notify(
                'Installing collected packages: %s' %
                ', '.join([req.name for req in to_install])
            )
        logger.indent += 2
        try:
            for requirement in to_install:

                # DISTRIBUTE TO SETUPTOOLS UPGRADE HACK (1 of 3 parts)
                # when upgrading from distribute-0.6.X to the new merged
                # setuptools in py2, we need to force setuptools to uninstall
                # distribute. In py3, which is always using distribute, this
                # conversion is already happening in distribute's
                # pkg_resources. It's ok *not* to check if setuptools>=0.7
                # because if someone were actually trying to ugrade from
                # distribute to setuptools 0.6.X, then all this could do is
                # actually help, although that upgade path was certainly never
                # "supported"
                # TODO: remove this later
                if requirement.name == 'setuptools':
                    try:
                        # only uninstall distribute<0.7. For >=0.7, setuptools
                        # will also be present, and that's what we need to
                        # uninstall
                        distribute_requirement = \
                            pkg_resources.Requirement.parse("distribute<0.7")
                        existing_distribute = \
                            pkg_resources.get_distribution("distribute")
                        if existing_distribute in distribute_requirement:
                            requirement.conflicts_with = existing_distribute
                    except pkg_resources.DistributionNotFound:
                        # distribute wasn't installed, so nothing to do
                        pass

                if requirement.conflicts_with:
                    logger.notify('Found existing installation: %s'
                                  % requirement.conflicts_with)
                    logger.indent += 2
                    try:
                        requirement.uninstall(auto_confirm=True)
                    finally:
                        logger.indent -= 2
                try:
                    requirement.install(
                        install_options,
                        global_options,
                        *args,
                        **kwargs
                    )
                except:
                    # if install did not succeed, rollback previous uninstall
                    if (requirement.conflicts_with
                            and not requirement.install_succeeded):
                        requirement.rollback_uninstall()
                    raise
                else:
                    if (requirement.conflicts_with
                            and requirement.install_succeeded):
                        requirement.commit_uninstall()
                requirement.remove_temporary_source()
        finally:
            logger.indent -= 2
        self.successfully_installed = to_install

    def create_bundle(self, bundle_filename):
        # FIXME: can't decide which is better; zip is easier to read
        # random files from, but tar.bz2 is smaller and not as lame a
        # format.

        # FIXME: this file should really include a manifest of the
        # packages, maybe some other metadata files.  It would make
        # it easier to detect as well.
        zip = zipfile.ZipFile(bundle_filename, 'w', zipfile.ZIP_DEFLATED)
        vcs_dirs = []
        for dir, basename in (self.build_dir, 'build'), (self.src_dir, 'src'):
            dir = os.path.normcase(os.path.abspath(dir))
            for dirpath, dirnames, filenames in os.walk(dir):
                for backend in vcs.backends:
                    vcs_backend = backend()
                    vcs_url = vcs_rev = None
                    if vcs_backend.dirname in dirnames:
                        for vcs_dir in vcs_dirs:
                            if dirpath.startswith(vcs_dir):
                                # vcs bundle file already in parent directory
                                break
                        else:
                            vcs_url, vcs_rev = vcs_backend.get_info(
                                os.path.join(dir, dirpath))
                            vcs_dirs.append(dirpath)
                        vcs_bundle_file = vcs_backend.bundle_file
                        vcs_guide = vcs_backend.guide % {'url': vcs_url,
                                                         'rev': vcs_rev}
                        dirnames.remove(vcs_backend.dirname)
                        break
                if 'pip-egg-info' in dirnames:
                    dirnames.remove('pip-egg-info')
                for dirname in dirnames:
                    dirname = os.path.join(dirpath, dirname)
                    name = self._clean_zip_name(dirname, dir)
                    zip.writestr(basename + '/' + name + '/', '')
                for filename in filenames:
                    if filename == PIP_DELETE_MARKER_FILENAME:
                        continue
                    filename = os.path.join(dirpath, filename)
                    name = self._clean_zip_name(filename, dir)
                    zip.write(filename, basename + '/' + name)
                if vcs_url:
                    name = os.path.join(dirpath, vcs_bundle_file)
                    name = self._clean_zip_name(name, dir)
                    zip.writestr(basename + '/' + name, vcs_guide)

        zip.writestr('pip-manifest.txt', self.bundle_requirements())
        zip.close()

    BUNDLE_HEADER = '''\
# This is a pip bundle file, that contains many source packages
# that can be installed as a group.  You can install this like:
#     pip this_file.zip
# The rest of the file contains a list of all the packages included:
'''

    def bundle_requirements(self):
        parts = [self.BUNDLE_HEADER]
        for req in [req for req in self.requirements.values()
                    if not req.comes_from]:
            parts.append('%s==%s\n' % (req.name, req.installed_version))
        parts.append(
            '# These packages were installed to satisfy the above '
            'requirements:\n'
        )
        for req in [req for req in self.requirements.values()
                    if req.comes_from]:
            parts.append('%s==%s\n' % (req.name, req.installed_version))
        # FIXME: should we do something with self.unnamed_requirements?
        return ''.join(parts)

    def _clean_zip_name(self, name, prefix):
        assert name.startswith(prefix + os.path.sep), (
            "name %r doesn't start with prefix %r" % (name, prefix)
        )
        name = name[len(prefix) + 1:]
        name = name.replace(os.path.sep, '/')
        return name
