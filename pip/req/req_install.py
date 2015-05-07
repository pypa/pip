from __future__ import absolute_import

import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile

from distutils.util import change_root
from distutils import sysconfig
from email.parser import FeedParser

from pip._vendor import pkg_resources, six
from pip._vendor.distlib.markers import interpret as markers_interpret
from pip._vendor.six.moves import configparser

import pip.wheel

from pip.compat import native_str, WINDOWS
from pip.download import is_url, url_to_path, path_to_url, is_archive_file
from pip.exceptions import (
    InstallationError, UninstallationError, UnsupportedWheel,
)
from pip.locations import (
    bin_py, running_under_virtualenv, PIP_DELETE_MARKER_FILENAME, bin_user,
)
from pip.utils import (
    display_path, rmtree, ask_path_exists, backup_dir, is_installable_dir,
    dist_in_usersite, dist_in_site_packages, egg_link_path,
    call_subprocess, read_text_file, FakeFile, _make_build_dir, ensure_dir,
    get_installed_version
)
from pip.utils.logging import indent_log
from pip.req.req_cache import CachedRequirement
from pip.req.req_uninstall import UninstallPathSet
from pip.vcs import vcs
from pip.wheel import move_wheel_files, Wheel
from pip._vendor.packaging.version import Version


logger = logging.getLogger(__name__)


def _strip_extras(path):
    m = re.match(r'^(.+)(\[[^\]]+\])$', path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


class InstallRequirement(object):

    def __init__(self, req, comes_from, editable=False,
                 link=None, as_egg=False, update=True, editable_options=None,
                 pycompile=True, markers=None, isolated=False, options=None,
                 wheel_cache=None, constraint=False):
        self.extras = ()
        if isinstance(req, six.string_types):
            req = pkg_resources.Requirement.parse(req)
            self.extras = req.extras

        self.req = req
        self.comes_from = comes_from
        self.constraint = constraint
        self.editable = editable

        if editable_options is None:
            editable_options = {}

        self.editable_options = editable_options
        self._wheel_cache = wheel_cache
        self.link = link
        self.as_egg = as_egg
        self.markers = markers
        self._egg_info_path = None
        # This holds the pkg_resources.Distribution object if this requirement
        # is already available:
        self.satisfied_by = None
        # This hold the pkg_resources.Distribution object if this requirement
        # conflicts with another installed distribution:
        self.conflicts_with = None
        # True if the editable should be updated:
        self.update = update
        # Set to True after successful installation
        self.install_succeeded = None
        # UninstallPathSet of uninstalled distribution (for possible rollback)
        self.uninstalled = None
        self.use_user_site = False
        self.target_dir = None
        self.options = options if options else {}
        self.pycompile = pycompile
        self.isolated = isolated
        # Where should temporary data for the requirement be written.
        self._req_cache = None
        # The cachable data for this requirement.
        self._cached_req = None
        # If this requirement is not being touched, why not?
        self.skip_reason = None

    @classmethod
    def from_editable(cls, editable_req, comes_from=None, default_vcs=None,
                      isolated=False, options=None, wheel_cache=None,
                      constraint=False):
        from pip.index import Link

        name, url, extras_override, editable_options = parse_editable(
            editable_req, default_vcs)

        res = cls(name, comes_from,
                  editable=True,
                  link=Link(url),
                  constraint=constraint,
                  editable_options=editable_options,
                  isolated=isolated,
                  options=options if options else {},
                  wheel_cache=wheel_cache)

        if extras_override is not None:
            res.extras = extras_override

        return res

    @classmethod
    def from_line(
            cls, name, comes_from=None, isolated=False, options=None,
            wheel_cache=None, constraint=False):
        """Creates an InstallRequirement from a name, which might be a
        requirement, directory containing 'setup.py', filename, or URL.
        """
        from pip.index import Link

        if is_url(name):
            marker_sep = '; '
        else:
            marker_sep = ';'
        if marker_sep in name:
            name, markers = name.split(marker_sep, 1)
            markers = markers.strip()
            if not markers:
                markers = None
        else:
            markers = None
        name = name.strip()
        req = None
        path = os.path.normpath(os.path.abspath(name))
        link = None
        extras = None

        if is_url(name):
            link = Link(name)
        else:
            p, extras = _strip_extras(path)
            if (os.path.isdir(p) and
                    (os.path.sep in name or name.startswith('.'))):

                if not is_installable_dir(p):
                    raise InstallationError(
                        "Directory %r is not installable. File 'setup.py' "
                        "not found." % name
                    )
                link = Link(path_to_url(p))
            elif is_archive_file(p):
                if not os.path.isfile(p):
                    logger.warning(
                        'Requirement %r looks like a filename, but the '
                        'file does not exist',
                        name
                    )
                link = Link(path_to_url(p))

        # it's a local file, dir, or url
        if link:
            # Handle relative file URLs
            if link.scheme == 'file' and re.search(r'\.\./', link.url):
                link = Link(
                    path_to_url(os.path.normpath(os.path.abspath(link.path))))
            # wheel file
            if link.is_wheel:
                wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
                if not wheel.supported():
                    raise UnsupportedWheel(
                        "%s is not a supported wheel on this platform." %
                        wheel.filename
                    )
                req = "%s==%s" % (wheel.name, wheel.version)
            else:
                # set the req to the egg fragment.  when it's not there, this
                # will become an 'unnamed' requirement
                req = link.egg_fragment

        # a requirement specifier
        else:
            req = name

        options = options if options else {}
        res = cls(req, comes_from, link=link, markers=markers,
                  isolated=isolated, options=options,
                  wheel_cache=wheel_cache, constraint=constraint)

        if extras:
            res.extras = pkg_resources.Requirement.parse('__placeholder__' +
                                                         extras).extras

        return res

    def __str__(self):
        if self.req:
            s = str(self.req)
            if self.link:
                s += ' from %s' % self.link.url
        else:
            s = self.link.url if self.link else None
        if self.satisfied_by is not None:
            s += ' in %s' % display_path(self.satisfied_by.location)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += ' (from %s)' % comes_from
        return s

    def __repr__(self):
        return '<%s object: %s editable=%r>' % (
            self.__class__.__name__, str(self), self.editable)

    def trace_label(self):
        """Provide a human readable description of this requirement.
        
        This is specifically for tracing in requirements resolution.
        """
        if self.name:
            label = self.name
        elif self.link.scheme == 'file':
            label = display_path(url_to_path(self.link.url))
        else:
            label = str(self)
        return label

    def populate_link(self, finder, upgrade):
        """Ensure that if a link can be found for this, that it is found.

        Note that self.link may still be None - if Upgrade is False and the
        requirement is already installed.
        """
        if self.link is None:
            self.link = finder.find_requirement(self, upgrade)

    @property
    def link(self):
        return self._link

    @link.setter
    def link(self, link):
        # Lookup a cached wheel, if possible.
        if self._wheel_cache is None:
            self._link = link
        else:
            self._link = self._wheel_cache.cached_wheel(link, self.name)
            if self._link != link:
                logger.debug('Using cached wheel link: %s', self._link)

    @property
    def req_cache(self):
        return self._req_cache

    @req_cache.setter
    def req_cache(self, req_cache):
        assert self._req_cache is None
        self._req_cache = req_cache

    @property
    def specifier(self):
        return self.req.specifier

    def from_path(self):
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += '->' + comes_from
        return s

    @property
    def build_path(self):
        assert self.req_cache is not None
        if self._cached_req is None:
            # Only ever encountered for user supplied req before we've done
            # resolution.
            cached_req = None
            if self.req:
                # The user has told us at least the name.
                name = self.req.project_name
                name = pkg_resources.safe_name(name).lower()
            else:
                name = None
            if not self.link:
                # We're looking up by constraints.
                url = None
                try:
                    # Oh the ugly. Finish the refactor Robert.
                    version = pkg_resources.parse_version(
                        self.req.specs[0][1])
                    cached_req = self.req_cache.lookup_name(name, version)
                except KeyError:
                    pass
            else:
                # Looking up by location
                url = self.link
                version = None
            # Probably try a lookup here and fallback otherwise?
            if cached_req is None:
                cached_req = CachedRequirement(
                    name=name, url=url, editable=self.editable,
                    editable_options=self.editable_options)
                self.req_cache.add(cached_req)
            self._cached_req = cached_req
        return self.req_cache.build_path(self._cached_req)

    def dist(self):
        # Make a concrete dist, only intended to be called:
        # - once
        # - before resolving, by the req_set setup code.
        # Get an appropriate handler and stash on the cached_req.
        # XXX: Make this a simpler, public method.
        self.build_path
        self._cached_req._abstract_dist = self._cached_req._inspect_disk(
            self.link)
        dist = self._cached_req.dist(self.req_cache)
        if (self._cached_req.name is None or
                self._cached_req.version is None):
            # URL / path requirement
            self.req_cache.update_name(
                self._cached_req, dist.project_name, dist.version)
            # Since the user requested a URL, no other versions are acceptable,
            # only this one. XXX: Future: setup-requires may still need other
            # versions so we'll want to be more nuanced in future.
            self.req_cache.lock_version(self._cached_req)
        # Capture the exact version that was chosen, vs perhaps vague user
        # input.
        self.req = pkg_resources.Requirement.parse(
            "%s===%s" % (dist.project_name, dist.version))
        return dist

    @property
    def name(self):
        if self.req is None:
            return None
        return native_str(self.req.project_name)

    @property
    def setup_py(self):
        assert self._cached_req
        assert self._cached_req.build_path, "No source dir for %s" % self
        try:
            import setuptools  # noqa
        except ImportError:
            # Setuptools is not available
            raise InstallationError(
                "setuptools must be installed to install from a source "
                "distribution"
            )

        setup_file = 'setup.py'

        if self.editable_options and 'subdirectory' in self.editable_options:
            setup_py = os.path.join(self.build_path,
                                    self.editable_options['subdirectory'],
                                    setup_file)

        else:
            setup_py = os.path.join(self.build_path, setup_file)

        # Python2 __file__ should not be unicode
        if six.PY2 and isinstance(setup_py, six.text_type):
            setup_py = setup_py.encode(sys.getfilesystemencoding())

        return setup_py

    def run_egg_info(self):
        assert self._cached_req.build_path
        if self.name:
            logger.debug(
                'Running setup.py (path:%s) egg_info for package %s',
                self.setup_py, self.name,
            )
        else:
            logger.debug(
                'Running setup.py (path:%s) egg_info for package from %s',
                self.setup_py, self.link,
            )

        with indent_log():
            script = self._run_setup_py
            script = script.replace('__SETUP_PY__', repr(self.setup_py))
            base_cmd = [sys.executable, '-c', script]
            if self.isolated:
                base_cmd += ["--no-user-cfg"]
            egg_info_cmd = base_cmd + ['egg_info']
            # We can't put the .egg-info files at the root, because then the
            # source code will be mistaken for an installed egg, causing
            # problems
            if self.editable:
                egg_base_option = []
            else:
                egg_info_dir = os.path.join(self.build_path, 'pip-egg-info')
                ensure_dir(egg_info_dir)
                egg_base_option = ['--egg-base', 'pip-egg-info']
            cwd = self.build_path
            if self.editable_options and \
                    'subdirectory' in self.editable_options:
                cwd = os.path.join(cwd, self.editable_options['subdirectory'])
            call_subprocess(
                egg_info_cmd + egg_base_option,
                cwd=cwd,
                show_stdout=False,
                command_level=logging.DEBUG,
                command_desc='python setup.py egg_info')

        if not self.req:
            if isinstance(
                    pkg_resources.parse_version(self.pkg_info()["Version"]),
                    Version):
                op = "=="
            else:
                op = "==="
            self.req = pkg_resources.Requirement.parse(
                "".join([
                    self.pkg_info()["Name"],
                    op,
                    self.pkg_info()["Version"],
                ]))

    # FIXME: This is a lame hack, entirely for PasteScript which has
    # a self-provided entry point that causes this awkwardness
    _run_setup_py = """
__file__ = __SETUP_PY__
from setuptools.command import egg_info
import pkg_resources
import os
import tokenize
def replacement_run(self):
    self.mkpath(self.egg_info)
    installer = self.distribution.fetch_build_egg
    for ep in pkg_resources.iter_entry_points('egg_info.writers'):
        # require=False is the change we're making:
        writer = ep.load(require=False)
        if writer:
            writer(self, ep.name, os.path.join(self.egg_info,ep.name))
    self.find_sources()
egg_info.egg_info.run = replacement_run
exec(compile(
    getattr(tokenize, 'open', open)(__file__).read().replace('\\r\\n', '\\n'),
    __file__,
    'exec'
))
"""

    def egg_info_data(self, filename):
        if self.satisfied_by is not None:
            if not self.satisfied_by.has_metadata(filename):
                return None
            return self.satisfied_by.get_metadata(filename)
        assert self.build_path
        filename = self.egg_info_path(filename)
        if not os.path.exists(filename):
            return None
        data = read_text_file(filename)
        return data

    def egg_info_path(self, filename):
        if self._egg_info_path is None:
            if self.editable:
                base = self.build_path
            else:
                base = os.path.join(self.build_path, 'pip-egg-info')
            filenames = os.listdir(base)
            if self.editable:
                filenames = []
                for root, dirs, files in os.walk(base):
                    for dir in vcs.dirnames:
                        if dir in dirs:
                            dirs.remove(dir)
                    # Iterate over a copy of ``dirs``, since mutating
                    # a list while iterating over it can cause trouble.
                    # (See https://github.com/pypa/pip/pull/462.)
                    for dir in list(dirs):
                        # Don't search in anything that looks like a virtualenv
                        # environment
                        if (
                                os.path.exists(
                                    os.path.join(root, dir, 'bin', 'python')
                                ) or
                                os.path.exists(
                                    os.path.join(
                                        root, dir, 'Scripts', 'Python.exe'
                                    )
                                )):
                            dirs.remove(dir)
                        # Also don't search through tests
                        elif dir == 'test' or dir == 'tests':
                            dirs.remove(dir)
                    filenames.extend([os.path.join(root, dir)
                                     for dir in dirs])
                filenames = [f for f in filenames if f.endswith('.egg-info')]

            if not filenames:
                raise InstallationError(
                    'No files/directories in %s (from %s)' % (base, filename)
                )
            assert filenames, \
                "No files/directories in %s (from %s)" % (base, filename)

            # if we have more than one match, we pick the toplevel one.  This
            # can easily be the case if there is a dist folder which contains
            # an extracted tarball for testing purposes.
            if len(filenames) > 1:
                filenames.sort(
                    key=lambda x: x.count(os.path.sep) +
                    (os.path.altsep and x.count(os.path.altsep) or 0)
                )
            self._egg_info_path = os.path.join(base, filenames[0])
        return os.path.join(self._egg_info_path, filename)

    def pkg_info(self):
        p = FeedParser()
        data = self.egg_info_data('PKG-INFO')
        if not data:
            logger.warning(
                'No PKG-INFO file found in %s',
                display_path(self.egg_info_path('PKG-INFO')),
            )
        p.feed(data or '')
        return p.close()

    _requirements_section_re = re.compile(r'\[(.*?)\]')

    @property
    def installed_version(self):
        return get_installed_version(self.name)

    def assert_source_matches_version(self):
        assert self._cached_req.build_path
        version = self.pkg_info()['version']
        if version not in self.req:
            logger.warning(
                'Requested %s, but installing version %s',
                self,
                self.installed_version,
            )
        else:
            logger.debug(
                'Source in %s has version %s, which satisfies requirement %s',
                display_path(self.build_path),
                version,
                self,
            )

    def update_editable(self, obtain=True):
        if not self.link:
            logger.debug(
                "Cannot update repository at %s; repository location is "
                "unknown",
                self.build_path,
            )
            return
        assert self.editable
        if self.link.scheme == 'file':
            # Static paths don't get updated
            return
        assert '+' in self.link.url, "bad url: %r" % self.link.url
        if not self.update:
            return
        vc_type, url = self.link.url.split('+', 1)
        backend = vcs.get_backend(vc_type)
        if not backend:
            raise AssertionError(
                'Unexpected version control type (in %s): %s'
                % (self.link, vc_type))
        vcs_backend = backend(self.link.url)
        if obtain:
            vcs_backend.obtain(self.build_path)
        else:
            vcs_backend.export(self.build_path)

    def uninstall(self, auto_confirm=False):
        """
        Uninstall the distribution currently satisfying this requirement.

        Prompts before removing or modifying files unless
        ``auto_confirm`` is True.

        Refuses to delete or modify files outside of ``sys.prefix`` -
        thus uninstallation within a virtual environment can only
        modify that virtual environment, even if the virtualenv is
        linked to global site-packages.

        """
        if not self.check_if_exists():
            raise UninstallationError(
                "Cannot uninstall requirement %s, not installed" % (self.name,)
            )
        dist = self.satisfied_by or self.conflicts_with

        paths_to_remove = UninstallPathSet(dist)
        develop_egg_link = egg_link_path(dist)
        develop_egg_link_egg_info = '{0}.egg-info'.format(
            pkg_resources.to_filename(dist.project_name))
        egg_info_exists = dist.egg_info and os.path.exists(dist.egg_info)
        # Special case for distutils installed package
        distutils_egg_info = getattr(dist._provider, 'path', None)

        # Uninstall cases order do matter as in the case of 2 installs of the
        # same package, pip needs to uninstall the currently detected version
        if (egg_info_exists and dist.egg_info.endswith('.egg-info') and
                not dist.egg_info.endswith(develop_egg_link_egg_info)):
            # if dist.egg_info.endswith(develop_egg_link_egg_info), we
            # are in fact in the develop_egg_link case
            paths_to_remove.add(dist.egg_info)
            if dist.has_metadata('installed-files.txt'):
                for installed_file in dist.get_metadata(
                        'installed-files.txt').splitlines():
                    path = os.path.normpath(
                        os.path.join(dist.egg_info, installed_file)
                    )
                    paths_to_remove.add(path)
            # FIXME: need a test for this elif block
            # occurs with --single-version-externally-managed/--record outside
            # of pip
            elif dist.has_metadata('top_level.txt'):
                if dist.has_metadata('namespace_packages.txt'):
                    namespaces = dist.get_metadata('namespace_packages.txt')
                else:
                    namespaces = []
                for top_level_pkg in [
                        p for p
                        in dist.get_metadata('top_level.txt').splitlines()
                        if p and p not in namespaces]:
                    path = os.path.join(dist.location, top_level_pkg)
                    paths_to_remove.add(path)
                    paths_to_remove.add(path + '.py')
                    paths_to_remove.add(path + '.pyc')

        elif distutils_egg_info:
            raise UninstallationError(
                "Detected a distutils installed project ({0!r}) which we "
                "cannot uninstall. The metadata provided by distutils does "
                "not contain a list of files which have been installed, so "
                "pip does not know which files to uninstall.".format(self.name)
            )

        elif dist.location.endswith('.egg'):
            # package installed by easy_install
            # We cannot match on dist.egg_name because it can slightly vary
            # i.e. setuptools-0.6c11-py2.6.egg vs setuptools-0.6rc11-py2.6.egg
            paths_to_remove.add(dist.location)
            easy_install_egg = os.path.split(dist.location)[1]
            easy_install_pth = os.path.join(os.path.dirname(dist.location),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, './' + easy_install_egg)

        elif develop_egg_link:
            # develop egg
            with open(develop_egg_link, 'r') as fh:
                link_pointer = os.path.normcase(fh.readline().strip())
            assert (link_pointer == dist.location), (
                'Egg-link %s does not match installed location of %s '
                '(at %s)' % (link_pointer, self.name, dist.location)
            )
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(os.path.dirname(develop_egg_link),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, dist.location)

        elif egg_info_exists and dist.egg_info.endswith('.dist-info'):
            for path in pip.wheel.uninstallation_paths(dist):
                paths_to_remove.add(path)

        else:
            logger.debug(
                'Not sure how to uninstall: %s - Check: %s',
                dist, dist.location)

        # find distutils scripts= scripts
        if dist.has_metadata('scripts') and dist.metadata_isdir('scripts'):
            for script in dist.metadata_listdir('scripts'):
                if dist_in_usersite(dist):
                    bin_dir = bin_user
                else:
                    bin_dir = bin_py
                paths_to_remove.add(os.path.join(bin_dir, script))
                if WINDOWS:
                    paths_to_remove.add(os.path.join(bin_dir, script) + '.bat')

        # find console_scripts
        if dist.has_metadata('entry_points.txt'):
            config = configparser.SafeConfigParser()
            config.readfp(
                FakeFile(dist.get_metadata_lines('entry_points.txt'))
            )
            if config.has_section('console_scripts'):
                for name, value in config.items('console_scripts'):
                    if dist_in_usersite(dist):
                        bin_dir = bin_user
                    else:
                        bin_dir = bin_py
                    paths_to_remove.add(os.path.join(bin_dir, name))
                    if WINDOWS:
                        paths_to_remove.add(
                            os.path.join(bin_dir, name) + '.exe'
                        )
                        paths_to_remove.add(
                            os.path.join(bin_dir, name) + '.exe.manifest'
                        )
                        paths_to_remove.add(
                            os.path.join(bin_dir, name) + '-script.py'
                        )

        paths_to_remove.remove(auto_confirm)
        self.uninstalled = paths_to_remove

    def rollback_uninstall(self):
        if self.uninstalled:
            self.uninstalled.rollback()
        else:
            logger.error(
                "Can't rollback %s, nothing uninstalled.", self.project_name,
            )

    def commit_uninstall(self):
        if self.uninstalled:
            self.uninstalled.commit()
        else:
            logger.error(
                "Can't commit %s, nothing uninstalled.", self.project_name,
            )

    def match_markers(self):
        if self.markers is not None:
            return markers_interpret(self.markers)
        else:
            return True

    def install(self, install_options, global_options=[], root=None):
        logger.info("Installing %s" % self.name)
        if self.editable:
            self.install_editable(install_options, global_options)
            return
        if self.is_wheel:
            version = pip.wheel.wheel_version(self.build_path)
            pip.wheel.check_compatibility(version, self.name)

            self.move_wheel_files(self.build_path, root=root)
            self.install_succeeded = True
            return

        # Extend the list of global and install options passed on to
        # the setup.py call with the ones from the requirements file.
        # Options specified in requirements file override those
        # specified on the command line, since the last option given
        # to setup.py is the one that is used.
        global_options += self.options.get('global_options', [])
        install_options += self.options.get('install_options', [])

        if self.isolated:
            global_options = list(global_options) + ["--no-user-cfg"]

        temp_location = tempfile.mkdtemp('-record', 'pip-')
        record_filename = os.path.join(temp_location, 'install-record.txt')
        try:
            install_args = [sys.executable]
            install_args.append('-c')
            install_args.append(
                "import setuptools, tokenize;__file__=%r;"
                "exec(compile(getattr(tokenize, 'open', open)(__file__).read()"
                ".replace('\\r\\n', '\\n'), __file__, 'exec'))" % self.setup_py
            )
            install_args += list(global_options) + \
                ['install', '--record', record_filename]

            if not self.as_egg:
                install_args += ['--single-version-externally-managed']

            if root is not None:
                install_args += ['--root', root]

            if self.pycompile:
                install_args += ["--compile"]
            else:
                install_args += ["--no-compile"]

            if running_under_virtualenv():
                py_ver_str = 'python' + sysconfig.get_python_version()
                install_args += ['--install-headers',
                                 os.path.join(sys.prefix, 'include', 'site',
                                              py_ver_str, self.name)]
            logger.info('Running setup.py install for %s', self.name)
            with indent_log():
                call_subprocess(
                    install_args + install_options,
                    cwd=self.build_path,
                    show_stdout=False,
                )

            if not os.path.exists(record_filename):
                logger.debug('Record file %s not found', record_filename)
                return
            self.install_succeeded = True
            if self.as_egg:
                # there's no --always-unzip option we can pass to install
                # command so we unable to save the installed-files.txt
                return

            def prepend_root(path):
                if root is None or not os.path.isabs(path):
                    return path
                else:
                    return change_root(root, path)

            with open(record_filename) as f:
                for line in f:
                    directory = os.path.dirname(line)
                    if directory.endswith('.egg-info'):
                        egg_info_dir = prepend_root(directory)
                        break
                else:
                    logger.warning(
                        'Could not find .egg-info directory in install record'
                        ' for %s',
                        self,
                    )
                    # FIXME: put the record somewhere
                    # FIXME: should this be an error?
                    return
            new_lines = []
            with open(record_filename) as f:
                for line in f:
                    filename = line.strip()
                    if os.path.isdir(filename):
                        filename += os.path.sep
                    new_lines.append(
                        os.path.relpath(
                            prepend_root(filename), egg_info_dir)
                    )
            inst_files_path = os.path.join(egg_info_dir, 'installed-files.txt')
            with open(inst_files_path, 'w') as f:
                f.write('\n'.join(new_lines) + '\n')
        finally:
            if os.path.exists(record_filename):
                os.remove(record_filename)
            rmtree(temp_location)

    def remove_temporary_source(self):
        """Remove the source files from this requirement, if they are marked
        for deletion"""
        if (self._cached_req and self._cached_req.build_path and 
            os.path.exists(
                os.path.join(self.build_path, PIP_DELETE_MARKER_FILENAME))):
            logger.debug('Removing source in %s', self.build_path)
            rmtree(self.build_path)
        if self._cached_req:
            self._cached_req.build_path = None

    def install_editable(self, install_options, global_options=()):
        logger.info('Running setup.py develop for %s', self.name)

        if self.isolated:
            global_options = list(global_options) + ["--no-user-cfg"]

        with indent_log():
            # FIXME: should we do --install-headers here too?
            cwd = self.build_path
            if self.editable_options and \
                    'subdirectory' in self.editable_options:
                cwd = os.path.join(cwd, self.editable_options['subdirectory'])
            call_subprocess(
                [
                    sys.executable,
                    '-c',
                    "import setuptools, tokenize; __file__=%r; exec(compile("
                    "getattr(tokenize, 'open', open)(__file__).read().replace"
                    "('\\r\\n', '\\n'), __file__, 'exec'))" % self.setup_py
                ] +
                list(global_options) +
                ['develop', '--no-deps'] +
                list(install_options),

                cwd=cwd,
                show_stdout=False)

        self.install_succeeded = True

    def check_if_exists(self):
        """Find an installed distribution that satisfies or conflicts
        with this requirement, and set self.satisfied_by or
        self.conflicts_with appropriately.
        """
        if self.req is None:
            return False
        try:
            self.satisfied_by = pkg_resources.get_distribution(self.req)
        except pkg_resources.DistributionNotFound:
            return False
        except pkg_resources.VersionConflict:
            existing_dist = pkg_resources.get_distribution(
                self.req.project_name
            )
            if self.use_user_site:
                if dist_in_usersite(existing_dist):
                    self.conflicts_with = existing_dist
                elif (running_under_virtualenv() and
                        dist_in_site_packages(existing_dist)):
                    raise InstallationError(
                        "Will not install to the user site because it will "
                        "lack sys.path precedence to %s in %s" %
                        (existing_dist.project_name, existing_dist.location)
                    )
            else:
                self.conflicts_with = existing_dist
        return True

    @property
    def is_wheel(self):
        return self.link and self.link.is_wheel

    def move_wheel_files(self, wheeldir, root=None):
        move_wheel_files(
            self.name, self.req, wheeldir,
            user=self.use_user_site,
            home=self.target_dir,
            root=root,
            pycompile=self.pycompile,
            isolated=self.isolated,
        )

    def get_dist(self):
        """Return a pkg_resources.Distribution built from self.egg_info_path"""
        egg_info = self.egg_info_path('').rstrip('/')
        base_dir = os.path.dirname(egg_info)
        metadata = pkg_resources.PathMetadata(base_dir, egg_info)
        dist_name = os.path.splitext(os.path.basename(egg_info))[0]
        return pkg_resources.Distribution(
            os.path.dirname(egg_info),
            project_name=dist_name,
            metadata=metadata)


def _strip_postfix(req):
    """
        Strip req postfix ( -dev, 0.2, etc )
    """
    # FIXME: use package_to_requirement?
    match = re.search(r'^(.*?)(?:-dev|-\d.*)$', req)
    if match:
        # Strip off -dev, -0.2, etc.
        req = match.group(1)
    return req


def _build_req_from_url(url):

    parts = [p for p in url.split('#', 1)[0].split('/') if p]

    req = None
    if parts[-2] in ('tags', 'branches', 'tag', 'branch'):
        req = parts[-3]
    elif parts[-1] == 'trunk':
        req = parts[-2]
    return req


def _build_editable_options(req):

    """
        This method generates a dictionary of the query string
        parameters contained in a given editable URL.
    """
    regexp = re.compile(r"[\?#&](?P<name>[^&=]+)=(?P<value>[^&=]+)")
    matched = regexp.findall(req)

    if matched:
        ret = dict()
        for option in matched:
            (name, value) = option
            if name in ret:
                raise Exception("%s option already defined" % name)
            ret[name] = value
        return ret
    return None


def parse_editable(editable_req, default_vcs=None):
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """

    url = editable_req
    extras = None

    # If a file path is specified with extras, strip off the extras.
    m = re.match(r'^(.+)(\[[^\]]+\])$', url)
    if m:
        url_no_extras = m.group(1)
        extras = m.group(2)
    else:
        url_no_extras = url

    if os.path.isdir(url_no_extras):
        if not os.path.exists(os.path.join(url_no_extras, 'setup.py')):
            raise InstallationError(
                "Directory %r is not installable. File 'setup.py' not found." %
                url_no_extras
            )
        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith('file:'):
        if extras:
            return (
                None,
                url_no_extras,
                pkg_resources.Requirement.parse(
                    '__placeholder__' + extras
                ).extras,
                {},
            )
        else:
            return None, url_no_extras, None, {}

    for version_control in vcs:
        if url.lower().startswith('%s:' % version_control):
            url = '%s+%s' % (version_control, url)
            break

    if '+' not in url:
        if default_vcs:
            url = default_vcs + '+' + url
        else:
            raise InstallationError(
                '%s should either be a path to a local project or a VCS url '
                'beginning with svn+, git+, hg+, or bzr+' %
                editable_req
            )

    vc_type = url.split('+', 1)[0].lower()

    if not vcs.get_backend(vc_type):
        error_message = 'For --editable=%s only ' % editable_req + \
            ', '.join([backend.name + '+URL' for backend in vcs.backends]) + \
            ' is currently supported'
        raise InstallationError(error_message)

    try:
        options = _build_editable_options(editable_req)
    except Exception as exc:
        raise InstallationError(
            '--editable=%s error in editable options:%s' % (editable_req, exc)
        )
    if not options or 'egg' not in options:
        req = _build_req_from_url(editable_req)
        if not req:
            raise InstallationError(
                '--editable=%s is not the right format; it must have '
                '#egg=Package' % editable_req
            )
    else:
        req = options['egg']

    package = _strip_postfix(req)
    return package, url, None, options


class _DistAbstraction(object):
    """Abstracts out the wheel vs non-wheel prepare_files logic.

    The requirements for anything installable are as follows:
     - we must be able to determine the requirement name
       (or we can't correctly handle the non-upgrade case).
     - we must be able to generate a list of run-time dependencies
       without installing any additional packages (or we would
       have to either burn time by doing temporary isolated installs
       or alternatively violate pips 'don't start installing unless
       all requirements are available' rule - neither of which are
       desirable).
     - for packages with setup requirements, we must also be able
       to determine their requirements without installing additional
       packages (for the same reason as run-time dependencies)
     - we must be able to create a Distribution object exposing the
       above metadata.
    """

    def __init__(self, path):
        self._path = path

    def dist(self, req_cache):
        """Return a setuptools Dist object."""
        raise NotImplementedError(self.dist)


class _IsWheel(_DistAbstraction):

    def dist(self, req_cache):
        return list(pkg_resources.find_distributions(
            self._path))[0]


class _IsSDist(_DistAbstraction):

    def __init__(self, path, editable_options, editable):
        super(_IsSDist, self).__init__(path)
        self._editable_options = editable_options
        self._editable = editable

    def dist(self, req_cache):
        logger.debug("Running setup.py egg_info for %s" % self._path)
        with indent_log():
            script = self._run_setup_py
            script = script.replace('__SETUP_PY__', repr(self.setup_py))
            base_cmd = [sys.executable, '-c', script]
            if req_cache.isolated:
                base_cmd += ["--no-user-cfg"]
            egg_info_cmd = base_cmd + ['egg_info']
            # We can't put the .egg-info files at the root, because then the
            # source code will be mistaken for an installed egg, causing
            # problems. editable installs will need the egg info moved into
            # the root during the install stage.
            egg_base_option = ['--egg-base', 'pip-egg-info']
            cwd = self._path
            cwd = os.path.join(
                self._path, self._editable_options.get('subdirectory', ''))
            egg_info_dir = os.path.join(cwd, 'pip-egg-info')
            ensure_dir(egg_info_dir)
            call_subprocess(
                egg_info_cmd + egg_base_option,
                cwd=cwd,
                show_stdout=False,
                command_level=logging.DEBUG,
                command_desc='python setup.py egg_info')

            # NB: editable installs need a root level .egg-info, but
            # we can move that into place later, and having a dedicated
            # directory m
            filenames = os.listdir(egg_info_dir)
            if not filenames:
                raise InstallationError(
                    'No files/directories in %s (from %s)'
                    % (egg_info_dir, filename))
        egg_info = os.path.join(egg_info_dir, filenames[0])
        metadata = pkg_resources.PathMetadata(egg_info_dir, egg_info)
        dist_name = os.path.splitext(filenames[0])[0]
        return pkg_resources.Distribution(
            os.path.dirname(egg_info),
            project_name=dist_name,
            metadata=metadata)

    # FIXME: This is a lame hack, entirely for PasteScript which has
    # a self-provided entry point that causes this awkwardness
    _run_setup_py = """
__file__ = __SETUP_PY__
from setuptools.command import egg_info
import pkg_resources
import os
import tokenize
def replacement_run(self):
    self.mkpath(self.egg_info)
    installer = self.distribution.fetch_build_egg
    for ep in pkg_resources.iter_entry_points('egg_info.writers'):
        # require=False is the change we're making:
        writer = ep.load(require=False)
        if writer:
            writer(self, ep.name, os.path.join(self.egg_info,ep.name))
    self.find_sources()
egg_info.egg_info.run = replacement_run
exec(compile(
    getattr(tokenize, 'open', open)(__file__).read().replace('\\r\\n', '\\n'),
    __file__,
    'exec'
))
"""

    @property
    def setup_py(self):
        try:
            import setuptools  # noqa
        except ImportError:
            # Setuptools is not available
            raise InstallationError(
                "setuptools must be installed to install from a source "
                "distribution"
            )

        subdir = self._editable_options.get('subdirectory', '')
        setup_py = os.path.join(self._path, subdir, 'setup.py')

        # Python2 __file__ should not be unicode
        if six.PY2 and isinstance(setup_py, six.text_type):
            setup_py = setup_py.encode(sys.getfilesystemencoding())

        return setup_py
