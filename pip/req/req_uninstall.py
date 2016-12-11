from __future__ import absolute_import

import csv
import functools
import logging
import os
import sys
import tempfile
import warnings

from pip._vendor import pkg_resources

from pip.compat import uses_pycache, WINDOWS, cache_from_source
from pip.compat import get_stdlib
from pip.exceptions import UninstallationError
from pip.locations import (
    bin_py, bin_user,
)
from pip.utils import (
    rmtree, ask, dist_in_usersite, is_local,
    egg_link_path, FakeFile,
    renames, normalize_path, dist_is_local,
)
from pip.utils.deprecation import RemovedInPip10Warning
from pip.utils.logging import indent_log


logger = logging.getLogger(__name__)


def _script_names(dist, script_name, is_gui):
    """Create the fully qualified name of the files created by
    {console,gui}_scripts for the given ``dist``.
    Returns the list of file names
    """
    if dist_in_usersite(dist):
        bin_dir = bin_user
    else:
        bin_dir = bin_py
    exe_name = os.path.join(bin_dir, script_name)
    paths_to_remove = [exe_name]
    if WINDOWS:
        paths_to_remove.append(exe_name + '.exe')
        paths_to_remove.append(exe_name + '.exe.manifest')
        if is_gui:
            paths_to_remove.append(exe_name + '-script.pyw')
        else:
            paths_to_remove.append(exe_name + '-script.py')
    return paths_to_remove


def _unique(fn):
    @functools.wraps(fn)
    def unique(*args, **kw):
        seen = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item
    return unique


@_unique
def uninstallation_paths(dist):
    """
    Yield all the uninstallation paths for dist based on RECORD-without-.pyc

    Yield paths to all the files in RECORD. For each .py file in RECORD, add
    the .pyc in the same directory.

    UninstallPathSet.add() takes care of the __pycache__ .pyc.
    """
    r = csv.reader(FakeFile(dist.get_metadata_lines('RECORD')))
    for row in r:
        path = os.path.join(dist.location, row[0])
        yield path
        if path.endswith('.py'):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            path = os.path.join(dn, base + '.pyc')
            yield path


class UninstallPathSet(object):
    """A set of file paths to be removed in the uninstallation of a
    requirement."""
    def __init__(self, dist):
        self.paths = set()
        self._refuse = set()
        self.pth = {}
        self.dist = dist
        self.save_dir = None
        self._moved_paths = []

    def _permitted(self, path):
        """
        Return True if the given path is one we are permitted to
        remove/modify, False otherwise.

        """
        return is_local(path)

    def add(self, path):
        head, tail = os.path.split(path)

        # we normalize the head to resolve parent directory symlinks, but not
        # the tail, since we only want to uninstall symlinks, not their targets
        path = os.path.join(normalize_path(head), os.path.normcase(tail))

        if not os.path.exists(path):
            return
        if self._permitted(path):
            self.paths.add(path)
        else:
            self._refuse.add(path)

        # __pycache__ files can show up after 'installed-files.txt' is created,
        # due to imports
        if os.path.splitext(path)[1] == '.py' and uses_pycache:
            self.add(cache_from_source(path))

    def add_pth(self, pth_file, entry):
        pth_file = normalize_path(pth_file)
        if self._permitted(pth_file):
            if pth_file not in self.pth:
                self.pth[pth_file] = UninstallPthEntries(pth_file)
            self.pth[pth_file].add(entry)
        else:
            self._refuse.add(pth_file)

    def compact(self, paths):
        """Compact a path set to contain the minimal number of paths
        necessary to contain all paths in the set. If /a/path/ and
        /a/path/to/a/file.txt are both in the set, leave only the
        shorter path."""
        short_paths = set()
        for path in sorted(paths, key=len):
            if not any([
                    (path.startswith(shortpath) and
                     path[len(shortpath.rstrip(os.path.sep))] == os.path.sep)
                    for shortpath in short_paths]):
                short_paths.add(path)
        return short_paths

    def _stash(self, path):
        return os.path.join(
            self.save_dir, os.path.splitdrive(path)[1].lstrip(os.path.sep))

    def remove(self, auto_confirm=False):
        """Remove paths in ``self.paths`` with confirmation (unless
        ``auto_confirm`` is True)."""
        if not self.paths:
            logger.info(
                "Can't uninstall '%s'. No files were found to uninstall.",
                self.dist.project_name,
            )
            return
        logger.info(
            'Uninstalling %s-%s:',
            self.dist.project_name, self.dist.version
        )

        with indent_log():
            paths = sorted(self.compact(self.paths))

            if auto_confirm:
                response = 'y'
            else:
                for path in paths:
                    logger.info(path)
                response = ask('Proceed (y/n)? ', ('y', 'n'))
            if self._refuse:
                logger.info('Not removing or modifying (outside of prefix):')
                for path in self.compact(self._refuse):
                    logger.info(path)
            if response == 'y':
                self.save_dir = tempfile.mkdtemp(suffix='-uninstall',
                                                 prefix='pip-')
                for path in paths:
                    new_path = self._stash(path)
                    logger.debug('Removing file or directory %s', path)
                    self._moved_paths.append(path)
                    renames(path, new_path)
                for pth in self.pth.values():
                    pth.remove()
                logger.info(
                    'Successfully uninstalled %s-%s',
                    self.dist.project_name, self.dist.version
                )

    def rollback(self):
        """Rollback the changes previously made by remove()."""
        if self.save_dir is None:
            logger.error(
                "Can't roll back %s; was not uninstalled",
                self.dist.project_name,
            )
            return False
        logger.info('Rolling back uninstall of %s', self.dist.project_name)
        for path in self._moved_paths:
            tmp_path = self._stash(path)
            logger.debug('Replacing %s', path)
            renames(tmp_path, path)
        for pth in self.pth.values():
            pth.rollback()

    def commit(self):
        """Remove temporary save dir: rollback will no longer be possible."""
        if self.save_dir is not None:
            rmtree(self.save_dir)
            self.save_dir = None
            self._moved_paths = []

    @classmethod
    def from_dist(cls, dist):
        dist_path = normalize_path(dist.location)
        if not dist_is_local(dist):
            logger.info(
                "Not uninstalling %s at %s, outside environment %s",
                dist.key,
                dist_path,
                sys.prefix,
            )
            return cls(dist)

        if dist_path in get_stdlib():
            logger.info(
                "Not uninstalling %s at %s, as it is in the standard library.",
                dist.key,
                dist_path,
            )
            return cls(dist)

        paths_to_remove = cls(dist)
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
                    paths_to_remove.add(path + '.pyo')

        elif distutils_egg_info:
            warnings.warn(
                "Uninstalling a distutils installed project ({0}) has been "
                "deprecated and will be removed in a future version. This is "
                "due to the fact that uninstalling a distutils project will "
                "only partially uninstall the project.".format(
                    dist.project_name),
                RemovedInPip10Warning,
            )
            paths_to_remove.add(distutils_egg_info)

        elif dist.location.endswith('.egg'):
            # package installed by easy_install
            # We cannot match on dist.egg_name because it can slightly vary
            # i.e. setuptools-0.6c11-py2.6.egg vs setuptools-0.6rc11-py2.6.egg
            paths_to_remove.add(dist.location)
            easy_install_egg = os.path.split(dist.location)[1]
            easy_install_pth = os.path.join(os.path.dirname(dist.location),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, './' + easy_install_egg)

        elif egg_info_exists and dist.egg_info.endswith('.dist-info'):
            for path in uninstallation_paths(dist):
                paths_to_remove.add(path)

        elif develop_egg_link:
            # develop egg
            with open(develop_egg_link, 'r') as fh:
                link_pointer = os.path.normcase(fh.readline().strip())
            assert (link_pointer == dist.location), (
                'Egg-link %s does not match installed location of %s '
                '(at %s)' % (link_pointer, dist.project_name, dist.location)
            )
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(os.path.dirname(develop_egg_link),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, dist.location)

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
        _scripts_to_remove = []
        console_scripts = dist.get_entry_map(group='console_scripts')
        for name in console_scripts.keys():
            _scripts_to_remove.extend(_script_names(dist, name, False))
        # find gui_scripts
        gui_scripts = dist.get_entry_map(group='gui_scripts')
        for name in gui_scripts.keys():
            _scripts_to_remove.extend(_script_names(dist, name, True))

        for s in _scripts_to_remove:
            paths_to_remove.add(s)

        return paths_to_remove


class UninstallPthEntries(object):
    def __init__(self, pth_file):
        if not os.path.isfile(pth_file):
            raise UninstallationError(
                "Cannot remove entries from nonexistent file %s" % pth_file
            )
        self.file = pth_file
        self.entries = set()
        self._saved_lines = None

    def add(self, entry):
        entry = os.path.normcase(entry)
        # On Windows, os.path.normcase converts the entry to use
        # backslashes.  This is correct for entries that describe absolute
        # paths outside of site-packages, but all the others use forward
        # slashes.
        if WINDOWS and not os.path.splitdrive(entry)[0]:
            entry = entry.replace('\\', '/')
        self.entries.add(entry)

    def remove(self):
        logger.debug('Removing pth entries from %s:', self.file)
        with open(self.file, 'rb') as fh:
            # windows uses '\r\n' with py3k, but uses '\n' with py2.x
            lines = fh.readlines()
            self._saved_lines = lines
        if any(b'\r\n' in line for line in lines):
            endline = '\r\n'
        else:
            endline = '\n'
        for entry in self.entries:
            try:
                logger.debug('Removing entry: %s', entry)
                lines.remove((entry + endline).encode("utf-8"))
            except ValueError:
                pass
        with open(self.file, 'wb') as fh:
            fh.writelines(lines)

    def rollback(self):
        if self._saved_lines is None:
            logger.error(
                'Cannot roll back changes to %s, none were made', self.file
            )
            return False
        logger.debug('Rolling %s back to previous state', self.file)
        with open(self.file, 'wb') as fh:
            fh.writelines(self._saved_lines)
        return True
