from __future__ import annotations

import functools
import os
import sys
import sysconfig
from collections import defaultdict
from collections.abc import Callable, Generator, Iterable
from importlib.util import cache_from_source
from typing import Any

from pip._internal.exceptions import LegacyDistutilsInstall, UninstallMissingRecord
from pip._internal.locations import get_bin_prefix, get_bin_user
from pip._internal.metadata import BaseDistribution
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.egg_link import egg_link_path_from_location
from pip._internal.utils.logging import getLogger, indent_log
from pip._internal.utils.misc import ask, normalize_path, renames, rmtree
from pip._internal.utils.temp_dir import AdjacentTempDirectory, TempDirectory
from pip._internal.utils.virtualenv import running_under_virtualenv

logger = getLogger(__name__)


def _script_names(
    bin_dir: str, script_name: str, is_gui: bool
) -> Generator[str, None, None]:
    """Create the fully qualified name of the files created by
    {console,gui}_scripts for the given ``dist``.
    Returns the list of file names
    """
    exe_name = os.path.join(bin_dir, script_name)
    yield exe_name
    if not WINDOWS:
        return
    yield f"{exe_name}.exe"
    yield f"{exe_name}.exe.manifest"
    if is_gui:
        yield f"{exe_name}-script.pyw"
    else:
        yield f"{exe_name}-script.py"


def _unique(
    fn: Callable[..., Generator[Any, None, None]],
) -> Callable[..., Generator[Any, None, None]]:
    @functools.wraps(fn)
    def unique(*args: Any, **kw: Any) -> Generator[Any, None, None]:
        seen: set[Any] = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item

    return unique


@_unique
def uninstallation_paths(dist: BaseDistribution) -> Generator[str, None, None]:
    """
    Yield all the uninstallation paths for dist based on RECORD-without-.py[co]

    Yield paths to all the files in RECORD. For each .py file in RECORD, add
    the .pyc and .pyo in the same directory.

    UninstallPathSet.add() takes care of the __pycache__ .py[co].

    If RECORD is not found, raises an error,
    with possible information from the INSTALLER file.

    https://packaging.python.org/specifications/recording-installed-packages/
    """
    location = dist.location
    assert location is not None, "not installed"

    entries = dist.iter_declared_entries()
    if entries is None:
        raise UninstallMissingRecord(distribution=dist)

    for entry in entries:
        path = os.path.join(location, entry)
        yield path
        if path.endswith(".py"):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            path = os.path.join(dn, base + ".pyc")
            yield path
            path = os.path.join(dn, base + ".pyo")
            yield path


def compact(paths: Iterable[str]) -> set[str]:
    """Compact a path set to contain the minimal number of paths
    necessary to contain all paths in the set. If /a/path/ and
    /a/path/to/a/file.txt are both in the set, leave only the
    shorter path."""

    sep = os.path.sep
    short_paths: set[str] = set()
    prefixes: set[str] = set()

    for path in sorted(paths, key=len):
        current = path[:-1] if path.endswith(sep + "*") else path
        parent = current.rstrip(sep)
        while parent:
            if parent in prefixes:
                break
            next_parent = os.path.dirname(parent).rstrip(sep)
            parent = "" if next_parent == parent else next_parent
        else:
            short_paths.add(path)
            prefixes.add(current.rstrip(sep))
    return short_paths


def compress_for_rename(paths: Iterable[str]) -> set[str]:
    """Returns a set containing the paths that need to be renamed.

    This set may include directories when the original sequence of paths
    included every file on disk.
    """
    case_map = {os.path.normcase(p): p for p in paths}
    remaining = set(case_map)
    unchecked = sorted({os.path.split(p)[0] for p in case_map.values()}, key=len)
    wildcards: set[str] = set()

    def norm_join(*a: str) -> str:
        return os.path.normcase(os.path.join(*a))

    for root in unchecked:
        if any(os.path.normcase(root).startswith(w) for w in wildcards):
            # This directory has already been handled.
            continue

        all_files: set[str] = set()
        all_subdirs: set[str] = set()
        for dirname, subdirs, files in os.walk(root):
            all_subdirs.update(norm_join(root, dirname, d) for d in subdirs)
            all_files.update(norm_join(root, dirname, f) for f in files)
        # If all the files we found are in our remaining set of files to
        # remove, then remove them from the latter set and add a wildcard
        # for the directory.
        if not (all_files - remaining):
            remaining.difference_update(all_files)
            wildcards.add(root + os.sep)

    return set(map(case_map.__getitem__, remaining)) | wildcards


def compress_for_output_listing(paths: Iterable[str]) -> tuple[set[str], set[str]]:
    """Returns a tuple of 2 sets of which paths to display to user

    The first set contains paths that would be deleted. Files of a package
    are not added and the top-level directory of the package has a '*' added
    at the end - to signify that all it's contents are removed.

    The second set contains files that would have been skipped in the above
    folders.
    """

    will_remove = set(paths)
    will_skip = set()

    # Determine folders and files
    folders = set()
    files = set()
    for path in will_remove:
        if path.endswith(".pyc"):
            continue
        if path.endswith("__init__.py") or ".dist-info" in path:
            folders.add(os.path.dirname(path))
        files.add(path)

    _normcased_files = set(map(os.path.normcase, files))

    folders = compact(folders)

    # This walks the tree using os.walk to not miss extra folders
    # that might get added.
    for folder in folders:
        for dirpath, _, dirfiles in os.walk(folder):
            for fname in dirfiles:
                if fname.endswith(".pyc"):
                    continue

                file_ = os.path.join(dirpath, fname)
                if (
                    os.path.isfile(file_)
                    and os.path.normcase(file_) not in _normcased_files
                ):
                    # We are skipping this file. Add it to the set.
                    will_skip.add(file_)

    will_remove = files | {os.path.join(folder, "*") for folder in folders}

    return will_remove, will_skip


class StashedUninstallPathSet:
    """A set of file rename operations to stash files while
    tentatively uninstalling them."""

    def __init__(self) -> None:
        # Mapping from source file root to [Adjacent]TempDirectory
        # for files under that directory.
        self._save_dirs: dict[str, TempDirectory] = {}
        # (old path, new path) tuples for each move that may need
        # to be undone.
        self._moves: list[tuple[str, str]] = []

    def _get_directory_stash(self, path: str) -> str:
        """Stashes a directory.

        Directories are stashed adjacent to their original location if
        possible, or else moved/copied into the user's temp dir."""

        try:
            save_dir: TempDirectory = AdjacentTempDirectory(path)
        except OSError:
            save_dir = TempDirectory(kind="uninstall")
        self._save_dirs[os.path.normcase(path)] = save_dir

        return save_dir.path

    def _get_file_stash(self, path: str) -> str:
        """Stashes a file.

        If no root has been provided, one will be created for the directory
        in the user's temp directory."""
        path = os.path.normcase(path)
        head, old_head = os.path.dirname(path), None
        save_dir = None

        while head != old_head:
            try:
                save_dir = self._save_dirs[head]
                break
            except KeyError:
                pass
            head, old_head = os.path.dirname(head), head
        else:
            # Did not find any suitable root
            head = os.path.dirname(path)
            save_dir = TempDirectory(kind="uninstall")
            self._save_dirs[head] = save_dir

        relpath = os.path.relpath(path, head)
        if relpath and relpath != os.path.curdir:
            return os.path.join(save_dir.path, relpath)
        return save_dir.path

    def stash(self, path: str) -> str:
        """Stashes the directory or file and returns its new location.
        Handle symlinks as files to avoid modifying the symlink targets.
        """
        path_is_dir = os.path.isdir(path) and not os.path.islink(path)
        if path_is_dir:
            new_path = self._get_directory_stash(path)
        else:
            new_path = self._get_file_stash(path)

        self._moves.append((path, new_path))
        if path_is_dir and os.path.isdir(new_path):
            # If we're moving a directory, we need to
            # remove the destination first or else it will be
            # moved to inside the existing directory.
            # We just created new_path ourselves, so it will
            # be removable.
            os.rmdir(new_path)
        renames(path, new_path)
        return new_path

    def commit(self) -> None:
        """Commits the uninstall by removing stashed files."""
        for save_dir in self._save_dirs.values():
            save_dir.cleanup()
        self._moves = []
        self._save_dirs = {}

    def rollback(self) -> None:
        """Undoes the uninstall by moving stashed files back."""
        for p in self._moves:
            logger.info("Moving to %s\n from %s", *p)

        for new_path, path in self._moves:
            try:
                logger.debug("Replacing %s from %s", new_path, path)
                if os.path.isfile(new_path) or os.path.islink(new_path):
                    os.unlink(new_path)
                elif os.path.isdir(new_path):
                    rmtree(new_path)
                renames(path, new_path)
            except OSError as ex:
                logger.error("Failed to restore %s", new_path)
                logger.debug("Exception: %s", ex)

        self.commit()

    @property
    def can_rollback(self) -> bool:
        return bool(self._moves)


class UninstallPathSet:
    """A set of file paths to be removed in the uninstallation of a
    requirement."""

    def __init__(self, dist: BaseDistribution) -> None:
        self._paths: set[str] = set()
        self._refuse: set[str] = set()
        self._pth: dict[str, UninstallPthEntries] = {}
        self._dist = dist
        self._moved_paths = StashedUninstallPathSet()
        # Create local cache of normalize_path results. Creating an UninstallPathSet
        # can result in hundreds/thousands of redundant calls to normalize_path with
        # the same args, which hurts performance.
        self._normalize_path_cached = functools.lru_cache(normalize_path)

    def _permitted(self, path: str) -> bool:
        """
        Return True if the given path is one we are permitted to
        remove/modify, False otherwise.

        """
        # aka is_local, but caching normalized sys.prefix
        if not running_under_virtualenv():
            return True
        return path.startswith(self._normalize_path_cached(sys.prefix))

    def add(self, path: str) -> None:
        head, tail = os.path.split(path)

        # we normalize the head to resolve parent directory symlinks, but not
        # the tail, since we only want to uninstall symlinks, not their targets
        path = os.path.join(self._normalize_path_cached(head), os.path.normcase(tail))

        if not os.path.exists(path):
            return
        if self._permitted(path):
            self._paths.add(path)
        else:
            self._refuse.add(path)

        # __pycache__ files can show up after 'installed-files.txt' is created,
        # due to imports
        if os.path.splitext(path)[1] == ".py":
            self.add(cache_from_source(path))

    def add_pth(self, pth_file: str, entry: str) -> None:
        pth_file = self._normalize_path_cached(pth_file)
        if self._permitted(pth_file):
            if pth_file not in self._pth:
                self._pth[pth_file] = UninstallPthEntries(pth_file)
            self._pth[pth_file].add(entry)
        else:
            self._refuse.add(pth_file)

    def remove(self, auto_confirm: bool = False, verbose: bool = False) -> None:
        """Remove paths in ``self._paths`` with confirmation (unless
        ``auto_confirm`` is True)."""

        if not self._paths:
            logger.info(
                "Can't uninstall '%s'. No files were found to uninstall.",
                self._dist.raw_name,
            )
            return

        dist_name_version = f"{self._dist.raw_name}-{self._dist.raw_version}"
        logger.info("Uninstalling %s:", dist_name_version)

        with indent_log():
            if auto_confirm or self._allowed_to_proceed(verbose):
                moved = self._moved_paths

                for_rename = compress_for_rename(self._paths)

                for path in sorted(compact(for_rename)):
                    moved.stash(path)
                    logger.verbose("Removing file or directory %s", path)

                for pth in self._pth.values():
                    pth.remove()

                logger.info("Successfully uninstalled %s", dist_name_version)

    def _allowed_to_proceed(self, verbose: bool) -> bool:
        """Display which files would be deleted and prompt for confirmation"""

        def _display(msg: str, paths: Iterable[str]) -> None:
            if not paths:
                return

            logger.info(msg)
            with indent_log():
                for path in sorted(compact(paths)):
                    logger.info(path)

        if not verbose:
            will_remove, will_skip = compress_for_output_listing(self._paths)
        else:
            # In verbose mode, display all the files that are going to be
            # deleted.
            will_remove = set(self._paths)
            will_skip = set()

        _display("Would remove:", will_remove)
        _display("Would not remove (might be manually added):", will_skip)
        _display("Would not remove (outside of prefix):", self._refuse)
        if verbose:
            _display("Will actually move:", compress_for_rename(self._paths))

        return ask("Proceed (Y/n)? ", ("y", "n", "")) != "n"

    def rollback(self) -> None:
        """Rollback the changes previously made by remove()."""
        if not self._moved_paths.can_rollback:
            logger.error(
                "Can't roll back %s; was not uninstalled",
                self._dist.raw_name,
            )
            return
        logger.info("Rolling back uninstall of %s", self._dist.raw_name)
        self._moved_paths.rollback()
        for pth in self._pth.values():
            pth.rollback()

    def commit(self) -> None:
        """Remove temporary save dir: rollback will no longer be possible."""
        self._moved_paths.commit()

    @classmethod
    def from_dist(cls, dist: BaseDistribution) -> UninstallPathSet:
        dist_location = dist.location
        info_location = dist.info_location
        if dist_location is None:
            logger.info(
                "Not uninstalling %s since it is not installed",
                dist.canonical_name,
            )
            return cls(dist)

        normalized_dist_location = normalize_path(dist_location)
        if not dist.local:
            logger.info(
                "Not uninstalling %s at %s, outside environment %s",
                dist.canonical_name,
                normalized_dist_location,
                sys.prefix,
            )
            return cls(dist)

        if normalized_dist_location in {
            p
            for p in {sysconfig.get_path("stdlib"), sysconfig.get_path("platstdlib")}
            if p
        }:
            logger.info(
                "Not uninstalling %s at %s, as it is in the standard library.",
                dist.canonical_name,
                normalized_dist_location,
            )
            return cls(dist)

        paths_to_remove = cls(dist)
        develop_egg_link = egg_link_path_from_location(dist.raw_name)

        # Distribution is installed with metadata in a "flat" .egg-info
        # directory. This means it is not a modern .dist-info installation, an
        # egg, or legacy editable.
        setuptools_flat_installation = (
            dist.installed_with_setuptools_egg_info
            and info_location is not None
            and os.path.exists(info_location)
            # If dist is editable and the location points to a ``.egg-info``,
            # we are in fact in the legacy editable case.
            and not info_location.endswith(f"{dist.setuptools_filename}.egg-info")
        )

        # Uninstall cases order do matter as in the case of 2 installs of the
        # same package, pip needs to uninstall the currently detected version
        if setuptools_flat_installation:
            if info_location is not None:
                paths_to_remove.add(info_location)
            installed_files = dist.iter_declared_entries()
            if installed_files is not None:
                for installed_file in installed_files:
                    paths_to_remove.add(os.path.join(dist_location, installed_file))
            # FIXME: need a test for this elif block
            # occurs with --single-version-externally-managed/--record outside
            # of pip
            elif dist.is_file("top_level.txt"):
                try:
                    namespace_packages = dist.read_text("namespace_packages.txt")
                except FileNotFoundError:
                    namespaces = []
                else:
                    namespaces = namespace_packages.splitlines(keepends=False)
                for top_level_pkg in [
                    p
                    for p in dist.read_text("top_level.txt").splitlines()
                    if p and p not in namespaces
                ]:
                    path = os.path.join(dist_location, top_level_pkg)
                    paths_to_remove.add(path)
                    paths_to_remove.add(f"{path}.py")
                    paths_to_remove.add(f"{path}.pyc")
                    paths_to_remove.add(f"{path}.pyo")

        elif dist.installed_by_distutils:
            raise LegacyDistutilsInstall(distribution=dist)

        elif dist.installed_as_egg:
            # package installed by easy_install
            # We cannot match on dist.egg_name because it can slightly vary
            # i.e. setuptools-0.6c11-py2.6.egg vs setuptools-0.6rc11-py2.6.egg
            # XXX We use normalized_dist_location because dist_location my contain
            # a trailing / if the distribution is a zipped egg
            # (which is not a directory).
            paths_to_remove.add(normalized_dist_location)
            easy_install_egg = os.path.split(normalized_dist_location)[1]
            easy_install_pth = os.path.join(
                os.path.dirname(normalized_dist_location),
                "easy-install.pth",
            )
            paths_to_remove.add_pth(easy_install_pth, "./" + easy_install_egg)

        elif dist.installed_with_dist_info:
            for path in uninstallation_paths(dist):
                paths_to_remove.add(path)

        elif develop_egg_link:
            # PEP 660 modern editable is handled in the ``.dist-info`` case
            # above, so this only covers the setuptools-style editable.
            with open(develop_egg_link) as fh:
                link_pointer = os.path.normcase(fh.readline().strip())
                normalized_link_pointer = paths_to_remove._normalize_path_cached(
                    link_pointer
                )
            assert os.path.samefile(
                normalized_link_pointer, normalized_dist_location
            ), (
                f"Egg-link {develop_egg_link} (to {link_pointer}) does not match "
                f"installed location of {dist.raw_name} (at {dist_location})"
            )
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(
                os.path.dirname(develop_egg_link), "easy-install.pth"
            )
            paths_to_remove.add_pth(easy_install_pth, dist_location)

        else:
            logger.debug(
                "Not sure how to uninstall: %s - Check: %s",
                dist,
                dist_location,
            )

        if dist.in_usersite:
            bin_dir = get_bin_user()
        else:
            bin_dir = get_bin_prefix()

        # find distutils scripts= scripts
        try:
            for script in dist.iter_distutils_script_names():
                paths_to_remove.add(os.path.join(bin_dir, script))
                if WINDOWS:
                    paths_to_remove.add(os.path.join(bin_dir, f"{script}.bat"))
        except (FileNotFoundError, NotADirectoryError):
            pass

        # find console_scripts and gui_scripts
        def iter_scripts_to_remove(
            dist: BaseDistribution,
            bin_dir: str,
        ) -> Generator[str, None, None]:
            for entry_point in dist.iter_entry_points():
                if entry_point.group == "console_scripts":
                    yield from _script_names(bin_dir, entry_point.name, False)
                elif entry_point.group == "gui_scripts":
                    yield from _script_names(bin_dir, entry_point.name, True)

        for s in iter_scripts_to_remove(dist, bin_dir):
            paths_to_remove.add(s)

        return paths_to_remove


class UninstallPthEntries:
    def __init__(self, pth_file: str) -> None:
        self.file = pth_file
        self.entries: set[str] = set()
        self._saved_lines: list[bytes] | None = None

    def add(self, entry: str) -> None:
        entry = os.path.normcase(entry)
        # On Windows, os.path.normcase converts the entry to use
        # backslashes.  This is correct for entries that describe absolute
        # paths outside of site-packages, but all the others use forward
        # slashes.
        # os.path.splitdrive is used instead of os.path.isabs because isabs
        # treats non-absolute paths with drive letter markings like c:foo\bar
        # as absolute paths. It also does not recognize UNC paths if they don't
        # have more than "\\sever\share". Valid examples: "\\server\share\" or
        # "\\server\share\folder".
        if WINDOWS and not os.path.splitdrive(entry)[0]:
            entry = entry.replace("\\", "/")
        self.entries.add(entry)

    def remove(self) -> None:
        logger.verbose("Removing pth entries from %s:", self.file)

        # If the file doesn't exist, log a warning and return
        if not os.path.isfile(self.file):
            logger.warning("Cannot remove entries from nonexistent file %s", self.file)
            return
        with open(self.file, "rb") as fh:
            # windows uses '\r\n' with py3k, but uses '\n' with py2.x
            lines = fh.readlines()
            self._saved_lines = lines
        if any(b"\r\n" in line for line in lines):
            endline = "\r\n"
        else:
            endline = "\n"
        # handle missing trailing newline
        if lines and not lines[-1].endswith(endline.encode("utf-8")):
            lines[-1] = lines[-1] + endline.encode("utf-8")
        for entry in self.entries:
            try:
                logger.verbose("Removing entry: %s", entry)
                lines.remove((entry + endline).encode("utf-8"))
            except ValueError:
                pass
        with open(self.file, "wb") as fh:
            fh.writelines(lines)

    def rollback(self) -> bool:
        if self._saved_lines is None:
            logger.error("Cannot roll back changes to %s, none were made", self.file)
            return False
        logger.debug("Rolling %s back to previous state", self.file)
        with open(self.file, "wb") as fh:
            fh.writelines(self._saved_lines)
        return True


class PathCompactor:
    """
    Like a trash compactor, but less destructive (hopefully).

    Remember: garbage in, garbage out.
    """

    def __init__(self, paths: Iterable[str], preserved_roots: Iterable[str] | None):
        self._paths_o = set(paths)
        self._preserved_roots_ns2os: dict[str, str] = {}
        if preserved_roots:
            for root in preserved_roots:
                root = os.path.join(root, "")
                self._preserved_roots_ns2os[os.path.normcase(root)] = root
        self._case_map_n2o: dict[str, str] = {}
        self._remaining_n: set[str] = set()
        self._manifest_by_dir_ns2n: dict[str, set[str]] = defaultdict(set)
        self._potential_roots_ns2os: dict[str, str] = {}
        self._roots_os: list[str] = []
        self._owned_paths_ns: set[str] = set()
        self._final_wildcards_ns2os: dict[str, str] = {}
        self._skipped_files_o: set[str] = set()
        self._skipped_dirs_o: set[str] = set()

    @property
    def paths(self) -> Iterable[str]:
        return self._paths_o

    def _parse_paths(self) -> None:
        sep = os.sep
        # All paths are treated like files. By keeping it this way we avoid the
        # need to stat each path to determine if it's a file/symlink/directory
        # and make special case decisions. Those are deferred until the roots
        # are iterated and the directory entries are compared to the paths in
        # the list generated here.
        #
        # This works because if a file/symlink comes in, the parent directory is
        # a potential root. When that directory gets iterated, we identify the
        # file and clear it for removal. Unrecognized files in that parent
        # directory prevent the folder from collapsing and becoming a wildcard.
        #
        # If a directory comes in, since we treat it like a file, its parent
        # directory is added to potential roots and is then iterated over. When
        # os.scandir returns the entry, it's identified as a directory type and
        # we see it in the list of files schedule for removal, we treat it like
        # a wildcard. Additional entries in that parent directory that are not
        # scheduled for removal poison the parent for collapsing, but the path
        # ID'd as a wildcard and all child directories do collapse.
        #
        # The most common use case will be __pycache__ directories which will be
        # siblings to .py files in a package directory. Since the .py files will
        # be in the RECORD anyway, there's a good chance these will collapse.
        # The exception will be packages that install files in <purelib>, like
        # six and typing_extensions, which will cause __pycache__ to be generated
        # at that level. The parent directory will be <purelib> but the other
        # entries in the directory will poison it and prevent it being wildcarded.
        #
        # In order to ensure the parent of the directory passed in is added to
        # the potential roots to be iterated on, the path entry here must not
        # a trailing slash so os.path.dirname gets the parent.
        for path_o in self._paths_o:
            # strip trailing separators in case a directory comes in with one
            path_o = path_o.rstrip(sep)

            path_n = os.path.normcase(path_o)
            p_dir_n = os.path.dirname(path_n)
            # We're assuming the parent directory isn't the root of a filesystem
            p_dir_ns = p_dir_n + sep

            self._case_map_n2o[path_n] = path_o
            self._remaining_n.add(path_n)
            self._manifest_by_dir_ns2n[p_dir_ns].add(path_n)

            if p_dir_ns not in self._potential_roots_ns2os:
                p_dir_o = os.path.dirname(path_o)
                self._potential_roots_ns2os[p_dir_ns] = p_dir_o + sep

    def _calculate_roots_and_owned_paths(self) -> None:
        # We need to sweep through the files list to determine the roots to iterate
        # and to determine what paths we may own.
        #
        # This may seems unnecessary since all potential roots are owned paths,
        # but it is important to determine what level of parent paths are owned
        # since roots can be influenced by information from the distribution.
        #
        # For:
        #   <purelib>/pkg/ns/module1/file.py
        #   <purelib>/pkg/ns/module2/file.py
        #
        # The roots will be
        #   <purelib>/pkg/ns/module1/
        #   <purelib>/pkg/ns/module2/
        #
        # The safest assumption using a naive search is that we can collapse and
        # remove the module1 and module2 directories, but not necessarily pkg/ns/
        # or pkg/ because we do not know how far up the directory hierarchy we can
        # safely traverse to perform removal and may traverse up to or past <purelib>/
        # and attempt to remove that path if it was the final package being removed.
        #
        # However, when informed that the installation root is <purelib>/ we know
        # we will never traverse above this path and it can be inferred that all
        # components subsequent to <purelib>/ are owned paths and are thus subject
        # to being collapsed if all files below them have been removed.
        #
        # We obviously cannot assume that everything subsequent to a root is an
        # owned path lest we potentially remove <purelib>/pkg/ns/module3/ which
        # may not be described in the path list and whose presence should prevent
        # the path from being collapsed as a wildcard for removal.
        #
        # If I were better at discrete math, I could write this as a formula but
        # in English it's the set of paths that share a root ancestor which lie
        # on any lineage path terminating at a potential root.
        #
        # The paths calculated here become candidates for wildcards if all files
        # beneath them are removed.
        sep = os.sep
        root_candidates_ns2os = self._potential_roots_ns2os.copy()

        # Add the preserved roots into the candidates
        if self._preserved_roots_ns2os:
            root_candidates_ns2os.update(self._preserved_roots_ns2os)

        # Sort alphabetically by normalized path string keys
        sorted_candidates_ns = sorted(root_candidates_ns2os.keys())

        if not sorted_candidates_ns:
            return

        # Because it's normalized and sorted, children *must* come after parents
        # so the first entry is always a root.
        current_root_ns = sorted_candidates_ns[0]
        self._roots_os.append(root_candidates_ns2os[current_root_ns])
        self._owned_paths_ns.add(current_root_ns)

        for candidate_ns in sorted_candidates_ns[1:]:
            # If the next path starts with our current active root, it's a child
            # directory whose lineage we need to add to the set of owned paths
            if candidate_ns.startswith(current_root_ns):
                # Climb upwards to register all intermediate directories as owned.
                # We stop as soon as we hit a lineage we've already registered
                # (which will eventually be the current_root_ns).
                curr_ns = candidate_ns
                while curr_ns not in self._owned_paths_ns:
                    self._owned_paths_ns.add(curr_ns)
                    curr_ns = os.path.dirname(curr_ns.rstrip(os.sep)) + sep
            else:  # We found a new root to traverse
                current_root_ns = candidate_ns
                self._roots_os.append(root_candidates_ns2os[current_root_ns])
                self._owned_paths_ns.add(current_root_ns)

    def _process_roots(self) -> None:
        sep = os.sep
        for root_os in self._roots_os:
            poisoned_dirs_ns: set[str] = set()

            stack = [(root_os, 0)]

            while stack:
                curr_os, state = stack.pop()
                # all entries in the stack are populated with a trailing slash
                curr_ns = os.path.normcase(curr_os)
                curr_n = curr_ns.rstrip(sep)

                if state == 0:
                    try:
                        entries = list(os.scandir(curr_os))
                    except OSError:
                        poisoned_dirs_ns.add(curr_ns)
                        continue

                    # Push self back with State 1 (to be processed AFTER children)
                    stack.append((curr_os, 1))

                    for entry in entries:
                        entry_n = os.path.normcase(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            entry_ns = entry_n + sep

                            # If this directory was explicitly listed in the RECORD, it
                            # should be treated as a wildcard. Wildcards do not allow
                            # "foreign" files or directories to prevent removal
                            if entry_n in self._remaining_n:
                                # Register it as a wildcard immediately
                                self._final_wildcards_ns2os[entry_ns] = entry.path + sep

                                # Search the list of directories for paths that
                                # are under our wildcard and need to be removed
                                dirs_to_wipe_ns = [
                                    d_ns
                                    for d_ns in self._manifest_by_dir_ns2n
                                    if d_ns.startswith(entry_ns) or d_ns == entry_ns
                                ]

                                # Wipe all associated files from remaining
                                # and shrink the manifest mapping
                                for d_ns in dirs_to_wipe_ns:
                                    self._remaining_n.difference_update(
                                        self._manifest_by_dir_ns2n.pop(d_ns)
                                    )

                                # We also need to remove the explicit folder entry
                                # itself (which was acting as a file in _remaining)
                                self._remaining_n.discard(entry_n)

                                # Skip traversal, we own it all.
                                continue

                            if entry_ns in self._owned_paths_ns:
                                # Push child to be visited
                                stack.append((entry.path + sep, 0))
                            else:
                                poisoned_dirs_ns.add(curr_ns)
                                self._skipped_dirs_o.add(entry.path)
                        else:
                            if entry_n not in self._remaining_n:
                                poisoned_dirs_ns.add(curr_ns)
                                self._skipped_files_o.add(entry.path)
                else:
                    protected = (
                        False
                        if not self._preserved_roots_ns2os
                        else curr_ns in self._preserved_roots_ns2os
                    )
                    # Are we poisoned by a foreign file or an un-collapsible child
                    # or are we within a path protected from wildcards
                    if curr_ns in poisoned_dirs_ns or protected:
                        # Bubble poison up to parent
                        poisoned_dirs_ns.add(os.path.dirname(curr_n) + sep)
                        continue

                    # Because we evaluate bottom-up, child wildcards are already
                    # in the dictionary. If this parent is now collapsing, those
                    # children are redundant and should be swallowed.
                    redundant_wildcards_ns = [
                        w_ns
                        for w_ns in self._final_wildcards_ns2os
                        if w_ns.startswith(curr_ns)
                    ]
                    for w_ns in redundant_wildcards_ns:
                        del self._final_wildcards_ns2os[w_ns]

                    # Add the parent wildcard
                    self._final_wildcards_ns2os[curr_ns] = curr_os

                    # Now delete any entries from remaining that we expected but
                    # didn't find because they may have been deleted otherwise.
                    # Note that the current directory may not have any direct
                    # manifest entries if the path was calculated from a protected
                    # root directory (e.g. namespace path with no immediate file)
                    expected_here_n = self._manifest_by_dir_ns2n.pop(curr_ns, set())
                    self._remaining_n.difference_update(expected_here_n)
                    self._remaining_n.discard(curr_n)

    def compress_for_rename(self) -> set[str]:
        return {self._case_map_n2o[p] for p in self._remaining_n} | set(
            self._final_wildcards_ns2os.values()
        )

    def compress_for_output_listing(self) -> tuple[set[str], set[str]]:
        # Unlike `compress_for_rename`, the values of the files in the "will remove"
        # set rely on looking only at the parent directories of files that were
        # specified in the original list of paths to determine the output; this
        # means that regardless of whether the roots were preserved and additional
        # directories were traversed, the output will not change. The "to skip"
        # paths, however, do factor in the roots iterated over, thus the files
        # must be filtered to exclude files that are not globbed by a prefix of
        # a reported wild card to control senseless noise.

        will_remove = {self._case_map_n2o[p] for p in self._remaining_n}

        parent_paths_ns = set(self._potential_roots_ns2os.keys())

        # removed preserved roots so they are not reported as wildcards
        parent_paths_ns -= set(self._preserved_roots_ns2os.keys())

        skipped_files = set()
        for candidate in self._skipped_files_o:
            candidate_n = os.path.normcase(candidate)
            for d_ns in parent_paths_ns:
                if candidate_n.startswith(d_ns):
                    skipped_files.add(candidate)
                    break

        for candidate in self._skipped_dirs_o:
            candidate_n = os.path.normcase(candidate)
            for d_ns in parent_paths_ns:
                if candidate_n.startswith(d_ns):
                    skipped_files.add(os.path.join(candidate, "") + "*")
                    break

        will_remove.update(
            {
                path_os + "*"
                for path_os in compact(
                    [self._potential_roots_ns2os[root] for root in parent_paths_ns]
                )
            }
        )

        return will_remove, skipped_files
