import json
import os
import re
import shutil
import site
import subprocess
import sys
import textwrap
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from textwrap import dedent
from typing import List, Optional
from zipfile import ZipFile

import pytest
from pip._vendor.packaging.utils import canonicalize_name
from scripttest import FoundDir, TestFileEnvironment

from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.locations import get_major_minor_version
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.network.session import PipSession
from pip._internal.utils.deprecation import DEPRECATION_MSG_PREFIX
from tests.lib.path import Path, curdir
from tests.lib.wheel import make_wheel

DATA_DIR = Path(__file__).parent.parent.joinpath("data").resolve()
SRC_DIR = Path(__file__).resolve().parent.parent.parent

pyversion = get_major_minor_version()

CURRENT_PY_VERSION_INFO = sys.version_info[:3]


def assert_paths_equal(actual, expected):
    assert os.path.normpath(actual) == os.path.normpath(expected)


def path_to_url(path):
    """
    Convert a path to URI. The path will be made absolute and
    will not have quoted path parts.
    (adapted from pip.util)
    """
    path = os.path.normpath(os.path.abspath(path))
    drive, path = os.path.splitdrive(path)
    filepath = path.split(os.path.sep)
    url = "/".join(filepath)
    if drive:
        # Note: match urllib.request.pathname2url's
        # behavior: uppercase the drive letter.
        return "file:///" + drive.upper() + url
    return "file://" + url


def _test_path_to_file_url(path):
    """
    Convert a test Path to a "file://" URL.

    Args:
      path: a tests.lib.path.Path object.
    """
    return "file://" + path.resolve().replace("\\", "/")


def create_file(path, contents=None):
    """Create a file on the path, with the given contents"""
    from pip._internal.utils.misc import ensure_dir

    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        if contents is not None:
            f.write(contents)
        else:
            f.write("\n")


def make_test_search_scope(
    find_links: Optional[List[str]] = None,
    index_urls: Optional[List[str]] = None,
):
    if find_links is None:
        find_links = []
    if index_urls is None:
        index_urls = []

    return SearchScope.create(find_links=find_links, index_urls=index_urls)


def make_test_link_collector(
    find_links: Optional[List[str]] = None,
    index_urls: Optional[List[str]] = None,
    session: Optional[PipSession] = None,
) -> LinkCollector:
    """
    Create a LinkCollector object for testing purposes.
    """
    if session is None:
        session = PipSession()

    search_scope = make_test_search_scope(
        find_links=find_links,
        index_urls=index_urls,
    )

    return LinkCollector(session=session, search_scope=search_scope)


def make_test_finder(
    find_links: Optional[List[str]] = None,
    index_urls: Optional[List[str]] = None,
    allow_all_prereleases: bool = False,
    session: Optional[PipSession] = None,
    target_python: Optional[TargetPython] = None,
) -> PackageFinder:
    """
    Create a PackageFinder for testing purposes.
    """
    link_collector = make_test_link_collector(
        find_links=find_links,
        index_urls=index_urls,
        session=session,
    )
    selection_prefs = SelectionPreferences(
        allow_yanked=True,
        allow_all_prereleases=allow_all_prereleases,
    )

    return PackageFinder.create(
        link_collector=link_collector,
        selection_prefs=selection_prefs,
        target_python=target_python,
    )


class TestData:
    """
    Represents a bundle of pre-created test data.

    This copies a pristine set of test data into a root location that is
    designed to be test specific. The reason for this is when running the tests
    concurrently errors can be generated because the related tooling uses
    the directory as a work space. This leads to two concurrent processes
    trampling over each other. This class gets around that by copying all
    data into a directory and operating on the copied data.
    """

    def __init__(self, root, source=None):
        self.source = source or DATA_DIR
        self.root = Path(root).resolve()

    @classmethod
    def copy(cls, root):
        obj = cls(root)
        obj.reset()
        return obj

    def reset(self):
        # Check explicitly for the target directory to avoid overly-broad
        # try/except.
        if self.root.exists():
            shutil.rmtree(self.root)
        shutil.copytree(self.source, self.root, symlinks=True)

    @property
    def packages(self):
        return self.root.joinpath("packages")

    @property
    def packages2(self):
        return self.root.joinpath("packages2")

    @property
    def packages3(self):
        return self.root.joinpath("packages3")

    @property
    def src(self):
        return self.root.joinpath("src")

    @property
    def indexes(self):
        return self.root.joinpath("indexes")

    @property
    def reqfiles(self):
        return self.root.joinpath("reqfiles")

    @property
    def completion_paths(self):
        return self.root.joinpath("completion_paths")

    @property
    def find_links(self):
        return path_to_url(self.packages)

    @property
    def find_links2(self):
        return path_to_url(self.packages2)

    @property
    def find_links3(self):
        return path_to_url(self.packages3)

    @property
    def backends(self):
        return path_to_url(self.root.joinpath("backends"))

    def index_url(self, index="simple"):
        return path_to_url(self.root.joinpath("indexes", index))


class TestFailure(AssertionError):
    """
    An "assertion" failed during testing.
    """

    pass


class TestPipResult:
    def __init__(self, impl, verbose=False):
        self._impl = impl

        if verbose:
            print(self.stdout)
            if self.stderr:
                print("======= stderr ========")
                print(self.stderr)
                print("=======================")

    def __getattr__(self, attr):
        return getattr(self._impl, attr)

    if sys.platform == "win32":

        @property
        def stdout(self):
            return self._impl.stdout.replace("\r\n", "\n")

        @property
        def stderr(self):
            return self._impl.stderr.replace("\r\n", "\n")

        def __str__(self):
            return str(self._impl).replace("\r\n", "\n")

    else:
        # Python doesn't automatically forward __str__ through __getattr__

        def __str__(self):
            return str(self._impl)

    def assert_installed(
        self,
        pkg_name,
        editable=True,
        with_files=None,
        without_files=None,
        without_egg_link=False,
        use_user_site=False,
        sub_dir=False,
    ):
        with_files = with_files or []
        without_files = without_files or []
        e = self.test_env

        if editable:
            pkg_dir = e.venv / "src" / pkg_name.lower()
            # If package was installed in a sub directory
            if sub_dir:
                pkg_dir = pkg_dir / sub_dir
        else:
            without_egg_link = True
            pkg_dir = e.site_packages / pkg_name

        if use_user_site:
            egg_link_path = e.user_site / pkg_name + ".egg-link"
        else:
            egg_link_path = e.site_packages / pkg_name + ".egg-link"

        if without_egg_link:
            if egg_link_path in self.files_created:
                raise TestFailure(
                    f"unexpected egg link file created: {egg_link_path!r}\n{self}"
                )
        else:
            if egg_link_path not in self.files_created:
                raise TestFailure(
                    f"expected egg link file missing: {egg_link_path!r}\n{self}"
                )

            egg_link_file = self.files_created[egg_link_path]
            egg_link_contents = egg_link_file.bytes.replace(os.linesep, "\n")

            # FIXME: I don't understand why there's a trailing . here
            if not (
                egg_link_contents.endswith("\n.")
                and egg_link_contents[:-2].endswith(pkg_dir)
            ):
                expected_ending = pkg_dir + "\n."
                raise TestFailure(
                    textwrap.dedent(
                        f"""
                        Incorrect egg_link file {egg_link_file!r}
                        Expected ending: {expected_ending!r}
                        ------- Actual contents -------
                        {egg_link_contents!r}
                        -------------------------------
                        """
                    ).strip()
                )

        if use_user_site:
            pth_file = e.user_site / "easy-install.pth"
        else:
            pth_file = e.site_packages / "easy-install.pth"

        if (pth_file in self.files_updated) == without_egg_link:
            maybe = "" if without_egg_link else "not "
            raise TestFailure(f"{pth_file} unexpectedly {maybe}updated by install")

        if (pkg_dir in self.files_created) == (curdir in without_files):
            maybe = "not " if curdir in without_files else ""
            files = sorted(self.files_created)
            raise TestFailure(
                textwrap.dedent(
                    f"""
                    expected package directory {pkg_dir!r} {maybe}to be created
                    actually created:
                    {files}
                    """
                )
            )

        for f in with_files:
            normalized_path = os.path.normpath(pkg_dir / f)
            if normalized_path not in self.files_created:
                raise TestFailure(
                    f"Package directory {pkg_dir!r} missing expected content {f!r}"
                )

        for f in without_files:
            normalized_path = os.path.normpath(pkg_dir / f)
            if normalized_path in self.files_created:
                raise TestFailure(
                    f"Package directory {pkg_dir!r} has unexpected content {f}"
                )

    def did_create(self, path, message=None):
        assert str(path) in self.files_created, _one_or_both(message, self)

    def did_not_create(self, path, message=None):
        assert str(path) not in self.files_created, _one_or_both(message, self)

    def did_update(self, path, message=None):
        assert str(path) in self.files_updated, _one_or_both(message, self)

    def did_not_update(self, path, message=None):
        assert str(path) not in self.files_updated, _one_or_both(message, self)


def _one_or_both(a, b):
    """Returns f"{a}\n{b}" if a is truthy, else returns str(b)."""
    if not a:
        return str(b)

    return f"{a}\n{b}"


def make_check_stderr_message(stderr, line, reason):
    """
    Create an exception message to use inside check_stderr().
    """
    return dedent(
        """\
    {reason}:
     Caused by line: {line!r}
     Complete stderr: {stderr}
    """
    ).format(stderr=stderr, line=line, reason=reason)


def _check_stderr(
    stderr,
    allow_stderr_warning,
    allow_stderr_error,
):
    """
    Check the given stderr for logged warnings and errors.

    :param stderr: stderr output as a string.
    :param allow_stderr_warning: whether a logged warning (or deprecation
        message) is allowed. Must be True if allow_stderr_error is True.
    :param allow_stderr_error: whether a logged error is allowed.
    """
    assert not (allow_stderr_error and not allow_stderr_warning)

    lines = stderr.splitlines()
    for line in lines:
        # First check for logging errors, which we don't allow during
        # tests even if allow_stderr_error=True (since a logging error
        # would signal a bug in pip's code).
        #    Unlike errors logged with logger.error(), these errors are
        # sent directly to stderr and so bypass any configured log formatter.
        # The "--- Logging error ---" string is used in Python 3.4+, and
        # "Logged from file " is used in Python 2.
        if line.startswith("--- Logging error ---") or line.startswith(
            "Logged from file "
        ):
            reason = "stderr has a logging error, which is never allowed"
            msg = make_check_stderr_message(stderr, line=line, reason=reason)
            raise RuntimeError(msg)
        if allow_stderr_error:
            continue

        if line.startswith("ERROR: "):
            reason = (
                "stderr has an unexpected error "
                "(pass allow_stderr_error=True to permit this)"
            )
            msg = make_check_stderr_message(stderr, line=line, reason=reason)
            raise RuntimeError(msg)
        if allow_stderr_warning:
            continue

        if line.startswith("WARNING: ") or line.startswith(DEPRECATION_MSG_PREFIX):
            reason = (
                "stderr has an unexpected warning "
                "(pass allow_stderr_warning=True to permit this)"
            )
            msg = make_check_stderr_message(stderr, line=line, reason=reason)
            raise RuntimeError(msg)


class PipTestEnvironment(TestFileEnvironment):
    """
    A specialized TestFileEnvironment for testing pip
    """

    #
    # Attribute naming convention
    # ---------------------------
    #
    # Instances of this class have many attributes representing paths
    # in the filesystem.  To keep things straight, absolute paths have
    # a name of the form xxxx_path and relative paths have a name that
    # does not end in '_path'.

    exe = sys.platform == "win32" and ".exe" or ""
    verbose = False

    def __init__(self, base_path, *args, virtualenv, pip_expect_warning=None, **kwargs):
        # Make our base_path a test.lib.path.Path object
        base_path = Path(base_path)

        # Store paths related to the virtual environment
        self.venv_path = virtualenv.location
        self.lib_path = virtualenv.lib
        self.site_packages_path = virtualenv.site
        self.bin_path = virtualenv.bin

        self.user_base_path = self.venv_path.joinpath("user")
        self.user_site_path = self.venv_path.joinpath(
            "user",
            site.USER_SITE[len(site.USER_BASE) + 1 :],
        )
        if sys.platform == "win32":
            scripts_base = Path(os.path.normpath(self.user_site_path.joinpath("..")))
            self.user_bin_path = scripts_base.joinpath("Scripts")
        else:
            self.user_bin_path = self.user_base_path.joinpath(
                os.path.relpath(self.bin_path, self.venv_path)
            )

        # Create a Directory to use as a scratch pad
        self.scratch_path = base_path.joinpath("scratch")
        self.scratch_path.mkdir()

        # Set our default working directory
        kwargs.setdefault("cwd", self.scratch_path)

        # Setup our environment
        environ = kwargs.setdefault("environ", os.environ.copy())
        environ["PATH"] = Path.pathsep.join(
            [self.bin_path] + [environ.get("PATH", [])],
        )
        environ["PYTHONUSERBASE"] = self.user_base_path
        # Writing bytecode can mess up updated file detection
        environ["PYTHONDONTWRITEBYTECODE"] = "1"
        # Make sure we get UTF-8 on output, even on Windows...
        environ["PYTHONIOENCODING"] = "UTF-8"

        # Whether all pip invocations should expect stderr
        # (useful for Python version deprecation)
        self.pip_expect_warning = pip_expect_warning

        # Call the TestFileEnvironment __init__
        super().__init__(base_path, *args, **kwargs)

        # Expand our absolute path directories into relative
        for name in [
            "base",
            "venv",
            "bin",
            "lib",
            "site_packages",
            "user_base",
            "user_site",
            "user_bin",
            "scratch",
        ]:
            real_name = f"{name}_path"
            relative_path = Path(
                os.path.relpath(getattr(self, real_name), self.base_path)
            )
            setattr(self, name, relative_path)

        # Make sure temp_path is a Path object
        self.temp_path = Path(self.temp_path)
        # Ensure the tmp dir exists, things break horribly if it doesn't
        self.temp_path.mkdir()

        # create easy-install.pth in user_site, so we always have it updated
        #   instead of created
        self.user_site_path.mkdir(parents=True)
        self.user_site_path.joinpath("easy-install.pth").touch()

    def _ignore_file(self, fn):
        if fn.endswith("__pycache__") or fn.endswith(".pyc"):
            result = True
        else:
            result = super()._ignore_file(fn)
        return result

    def _find_traverse(self, path, result):
        # Ignore symlinked directories to avoid duplicates in `run()`
        # results because of venv `lib64 -> lib/` symlink on Linux.
        full = os.path.join(self.base_path, path)
        if os.path.isdir(full) and os.path.islink(full):
            if not self.temp_path or path != "tmp":
                result[path] = FoundDir(self.base_path, path)
        else:
            super()._find_traverse(path, result)

    def run(
        self,
        *args,
        cwd=None,
        allow_stderr_error=None,
        allow_stderr_warning=None,
        allow_error=None,
        **kw,
    ):
        """
        :param allow_stderr_error: whether a logged error is allowed in
            stderr.  Passing True for this argument implies
            `allow_stderr_warning` since warnings are weaker than errors.
        :param allow_stderr_warning: whether a logged warning (or
            deprecation message) is allowed in stderr.
        :param allow_error: if True (default is False) does not raise
            exception when the command exit value is non-zero.  Implies
            expect_error, but in contrast to expect_error will not assert
            that the exit value is zero.
        :param expect_error: if False (the default), asserts that the command
            exits with 0.  Otherwise, asserts that the command exits with a
            non-zero exit code.  Passing True also implies allow_stderr_error
            and allow_stderr_warning.
        :param expect_stderr: whether to allow warnings in stderr (equivalent
            to `allow_stderr_warning`).  This argument is an abbreviated
            version of `allow_stderr_warning` and is also kept for backwards
            compatibility.
        """
        if self.verbose:
            print(f">> running {args} {kw}")

        cwd = cwd or self.cwd
        if sys.platform == "win32":
            # Partial fix for ScriptTest.run using `shell=True` on Windows.
            args = [str(a).replace("^", "^^").replace("&", "^&") for a in args]

        if allow_error:
            kw["expect_error"] = True

        # Propagate default values.
        expect_error = kw.get("expect_error")
        if expect_error:
            # Then default to allowing logged errors.
            if allow_stderr_error is not None and not allow_stderr_error:
                raise RuntimeError(
                    "cannot pass allow_stderr_error=False with expect_error=True"
                )
            allow_stderr_error = True

        elif kw.get("expect_stderr"):
            # Then default to allowing logged warnings.
            if allow_stderr_warning is not None and not allow_stderr_warning:
                raise RuntimeError(
                    "cannot pass allow_stderr_warning=False with expect_stderr=True"
                )
            allow_stderr_warning = True

        if allow_stderr_error:
            if allow_stderr_warning is not None and not allow_stderr_warning:
                raise RuntimeError(
                    "cannot pass allow_stderr_warning=False with "
                    "allow_stderr_error=True"
                )

        # Default values if not set.
        if allow_stderr_error is None:
            allow_stderr_error = False
        if allow_stderr_warning is None:
            allow_stderr_warning = allow_stderr_error

        # Pass expect_stderr=True to allow any stderr.  We do this because
        # we do our checking of stderr further on in check_stderr().
        kw["expect_stderr"] = True
        result = super().run(cwd=cwd, *args, **kw)

        if expect_error and not allow_error:
            if result.returncode == 0:
                __tracebackhide__ = True
                raise AssertionError("Script passed unexpectedly.")

        _check_stderr(
            result.stderr,
            allow_stderr_error=allow_stderr_error,
            allow_stderr_warning=allow_stderr_warning,
        )

        return TestPipResult(result, verbose=self.verbose)

    def pip(self, *args, use_module=True, **kwargs):
        __tracebackhide__ = True
        if self.pip_expect_warning:
            kwargs["allow_stderr_warning"] = True
        if use_module:
            exe = "python"
            args = ("-m", "pip") + args
        else:
            exe = "pip"
        return self.run(exe, *args, **kwargs)

    def pip_install_local(self, *args, **kwargs):
        return self.pip(
            "install",
            "--no-index",
            "--find-links",
            path_to_url(os.path.join(DATA_DIR, "packages")),
            *args,
            **kwargs,
        )

    def easy_install(self, *args, **kwargs):
        args = ("-m", "easy_install") + args
        return self.run("python", *args, **kwargs)

    def assert_installed(self, **kwargs):
        ret = self.pip("list", "--format=json")
        installed = set(
            (canonicalize_name(val["name"]), val["version"])
            for val in json.loads(ret.stdout)
        )
        expected = set((canonicalize_name(k), v) for k, v in kwargs.items())
        assert expected <= installed, "{!r} not all in {!r}".format(expected, installed)

    def assert_not_installed(self, *args):
        ret = self.pip("list", "--format=json")
        installed = set(
            canonicalize_name(val["name"]) for val in json.loads(ret.stdout)
        )
        # None of the given names should be listed as installed, i.e. their
        # intersection should be empty.
        expected = set(canonicalize_name(k) for k in args)
        assert not (expected & installed), "{!r} contained in {!r}".format(
            expected, installed
        )


# FIXME ScriptTest does something similar, but only within a single
# ProcResult; this generalizes it so states can be compared across
# multiple commands.  Maybe should be rolled into ScriptTest?
def diff_states(start, end, ignore=None):
    """
    Differences two "filesystem states" as represented by dictionaries
    of FoundFile and FoundDir objects.

    Returns a dictionary with following keys:

    ``deleted``
        Dictionary of files/directories found only in the start state.

    ``created``
        Dictionary of files/directories found only in the end state.

    ``updated``
        Dictionary of files whose size has changed (FIXME not entirely
        reliable, but comparing contents is not possible because
        FoundFile.bytes is lazy, and comparing mtime doesn't help if
        we want to know if a file has been returned to its earlier
        state).

    Ignores mtime and other file attributes; only presence/absence and
    size are considered.

    """
    ignore = ignore or []

    def prefix_match(path, prefix):
        if path == prefix:
            return True
        prefix = prefix.rstrip(os.path.sep) + os.path.sep
        return path.startswith(prefix)

    start_keys = {
        k for k in start.keys() if not any([prefix_match(k, i) for i in ignore])
    }
    end_keys = {k for k in end.keys() if not any([prefix_match(k, i) for i in ignore])}
    deleted = {k: start[k] for k in start_keys.difference(end_keys)}
    created = {k: end[k] for k in end_keys.difference(start_keys)}
    updated = {}
    for k in start_keys.intersection(end_keys):
        if start[k].size != end[k].size:
            updated[k] = end[k]
    return dict(deleted=deleted, created=created, updated=updated)


def assert_all_changes(start_state, end_state, expected_changes):
    """
    Fails if anything changed that isn't listed in the
    expected_changes.

    start_state is either a dict mapping paths to
    scripttest.[FoundFile|FoundDir] objects or a TestPipResult whose
    files_before we'll test.  end_state is either a similar dict or a
    TestPipResult whose files_after we'll test.

    Note: listing a directory means anything below
    that directory can be expected to have changed.
    """
    __tracebackhide__ = True

    start_files = start_state
    end_files = end_state
    if isinstance(start_state, TestPipResult):
        start_files = start_state.files_before
    if isinstance(end_state, TestPipResult):
        end_files = end_state.files_after

    diff = diff_states(start_files, end_files, ignore=expected_changes)
    if list(diff.values()) != [{}, {}, {}]:
        raise TestFailure(
            "Unexpected changes:\n"
            + "\n".join([k + ": " + ", ".join(v.keys()) for k, v in diff.items()])
        )

    # Don't throw away this potentially useful information
    return diff


def _create_main_file(dir_path, name=None, output=None):
    """
    Create a module with a main() function that prints the given output.
    """
    if name is None:
        name = "version_pkg"
    if output is None:
        output = "0.1"
    text = textwrap.dedent(
        f"""
        def main():
            print({output!r})
        """
    )
    filename = f"{name}.py"
    dir_path.joinpath(filename).write_text(text)


def _git_commit(
    env_or_script,
    repo_dir,
    message=None,
    allow_empty=False,
    stage_modified=False,
):
    """
    Run git-commit.

    Args:
      env_or_script: pytest's `script` or `env` argument.
      repo_dir: a path to a Git repository.
      message: an optional commit message.
    """
    if message is None:
        message = "test commit"

    args = []

    if allow_empty:
        args.append("--allow-empty")

    if stage_modified:
        args.append("--all")

    new_args = [
        "git",
        "commit",
        "-q",
        "--author",
        "pip <distutils-sig@python.org>",
    ]
    new_args.extend(args)
    new_args.extend(["-m", message])
    env_or_script.run(*new_args, cwd=repo_dir)


def _vcs_add(script, version_pkg_path, vcs="git"):
    if vcs == "git":
        script.run("git", "init", cwd=version_pkg_path)
        script.run("git", "add", ".", cwd=version_pkg_path)
        _git_commit(script, version_pkg_path, message="initial version")
    elif vcs == "hg":
        script.run("hg", "init", cwd=version_pkg_path)
        script.run("hg", "add", ".", cwd=version_pkg_path)
        script.run(
            "hg",
            "commit",
            "-q",
            "--user",
            "pip <distutils-sig@python.org>",
            "-m",
            "initial version",
            cwd=version_pkg_path,
        )
    elif vcs == "svn":
        repo_url = _create_svn_repo(script, version_pkg_path)
        script.run(
            "svn", "checkout", repo_url, "pip-test-package", cwd=script.scratch_path
        )
        checkout_path = script.scratch_path / "pip-test-package"

        # svn internally stores windows drives as uppercase; we'll match that.
        checkout_path = checkout_path.replace("c:", "C:")

        version_pkg_path = checkout_path
    elif vcs == "bazaar":
        script.run("bzr", "init", cwd=version_pkg_path)
        script.run("bzr", "add", ".", cwd=version_pkg_path)
        script.run(
            "bzr", "whoami", "pip <distutils-sig@python.org>", cwd=version_pkg_path
        )
        script.run(
            "bzr",
            "commit",
            "-q",
            "--author",
            "pip <distutils-sig@python.org>",
            "-m",
            "initial version",
            cwd=version_pkg_path,
        )
    else:
        raise ValueError(f"Unknown vcs: {vcs}")
    return version_pkg_path


def _create_test_package_with_subdirectory(script, subdirectory):
    script.scratch_path.joinpath("version_pkg").mkdir()
    version_pkg_path = script.scratch_path / "version_pkg"
    _create_main_file(version_pkg_path, name="version_pkg", output="0.1")
    version_pkg_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
            from setuptools import setup, find_packages

            setup(
                name="version_pkg",
                version="0.1",
                packages=find_packages(),
                py_modules=["version_pkg"],
                entry_points=dict(console_scripts=["version_pkg=version_pkg:main"]),
            )
            """
        )
    )

    subdirectory_path = version_pkg_path.joinpath(subdirectory)
    subdirectory_path.mkdir()
    _create_main_file(subdirectory_path, name="version_subpkg", output="0.1")

    subdirectory_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
            from setuptools import find_packages, setup

            setup(
                name="version_subpkg",
                version="0.1",
                packages=find_packages(),
                py_modules=["version_subpkg"],
                entry_points=dict(console_scripts=["version_pkg=version_subpkg:main"]),
            )
            """
        )
    )

    script.run("git", "init", cwd=version_pkg_path)
    script.run("git", "add", ".", cwd=version_pkg_path)
    _git_commit(script, version_pkg_path, message="initial version")

    return version_pkg_path


def _create_test_package_with_srcdir(script, name="version_pkg", vcs="git"):
    script.scratch_path.joinpath(name).mkdir()
    version_pkg_path = script.scratch_path / name
    subdir_path = version_pkg_path.joinpath("subdir")
    subdir_path.mkdir()
    src_path = subdir_path.joinpath("src")
    src_path.mkdir()
    pkg_path = src_path.joinpath("pkg")
    pkg_path.mkdir()
    pkg_path.joinpath("__init__.py").write_text("")
    subdir_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
                from setuptools import setup, find_packages
                setup(
                    name="{name}",
                    version="0.1",
                    packages=find_packages(),
                    package_dir={{"": "src"}},
                )
            """.format(
                name=name
            )
        )
    )
    return _vcs_add(script, version_pkg_path, vcs)


def _create_test_package(script, name="version_pkg", vcs="git"):
    script.scratch_path.joinpath(name).mkdir()
    version_pkg_path = script.scratch_path / name
    _create_main_file(version_pkg_path, name=name, output="0.1")
    version_pkg_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
                from setuptools import setup, find_packages
                setup(
                    name="{name}",
                    version="0.1",
                    packages=find_packages(),
                    py_modules=["{name}"],
                    entry_points=dict(console_scripts=["{name}={name}:main"]),
                )
            """.format(
                name=name
            )
        )
    )
    return _vcs_add(script, version_pkg_path, vcs)


def _create_svn_repo(script, version_pkg_path):
    repo_url = path_to_url(script.scratch_path / "pip-test-package-repo" / "trunk")
    script.run("svnadmin", "create", "pip-test-package-repo", cwd=script.scratch_path)
    script.run(
        "svn",
        "import",
        version_pkg_path,
        repo_url,
        "-m",
        "Initial import of pip-test-package",
        cwd=script.scratch_path,
    )
    return repo_url


def _change_test_package_version(script, version_pkg_path):
    _create_main_file(
        version_pkg_path, name="version_pkg", output="some different version"
    )
    # Pass -a to stage the change to the main file.
    _git_commit(script, version_pkg_path, message="messed version", stage_modified=True)


@contextmanager
def requirements_file(contents, tmpdir):
    """Return a Path to a requirements file of given contents.

    As long as the context manager is open, the requirements file will exist.

    :param tmpdir: A Path to the folder in which to create the file

    """
    path = tmpdir / "reqs.txt"
    path.write_text(contents)
    yield path
    path.unlink()


def create_test_package_with_setup(script, **setup_kwargs):
    assert "name" in setup_kwargs, setup_kwargs
    pkg_path = script.scratch_path / setup_kwargs["name"]
    pkg_path.mkdir()
    pkg_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            f"""
                from setuptools import setup
                kwargs = {setup_kwargs!r}
                setup(**kwargs)
            """
        )
    )
    return pkg_path


def urlsafe_b64encode_nopad(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_really_basic_wheel(name: str, version: str) -> bytes:
    def digest(contents):
        return "sha256={}".format(urlsafe_b64encode_nopad(sha256(contents).digest()))

    def add_file(path, text):
        contents = text.encode("utf-8")
        z.writestr(path, contents)
        records.append((path, digest(contents), str(len(contents))))

    dist_info = f"{name}-{version}.dist-info"
    record_path = f"{dist_info}/RECORD"
    records = [(record_path, "", "")]
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        add_file(f"{dist_info}/WHEEL", "Wheel-Version: 1.0")
        add_file(
            f"{dist_info}/METADATA",
            dedent(
                """\
                Metadata-Version: 2.1
                Name: {}
                Version: {}
                """.format(
                    name, version
                )
            ),
        )
        z.writestr(record_path, "\n".join(",".join(r) for r in records))
    buf.seek(0)
    return buf.read()


def create_basic_wheel_for_package(
    script,
    name,
    version,
    depends=None,
    extras=None,
    requires_python=None,
    extra_files=None,
):
    if depends is None:
        depends = []
    if extras is None:
        extras = {}
    if extra_files is None:
        extra_files = {}

    # Fix wheel distribution name by replacing runs of non-alphanumeric
    # characters with an underscore _ as per PEP 491
    name = re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)
    archive_name = f"{name}-{version}-py2.py3-none-any.whl"
    archive_path = script.scratch_path / archive_name

    package_init_py = f"{name}/__init__.py"
    assert package_init_py not in extra_files
    extra_files[package_init_py] = textwrap.dedent(
        """
        __version__ = {version!r}
        def hello():
            return "Hello From {name}"
        """,
    ).format(version=version, name=name)

    requires_dist = depends + [
        f'{package}; extra == "{extra}"'
        for extra, packages in extras.items()
        for package in packages
    ]

    metadata_updates = {
        "Provides-Extra": list(extras),
        "Requires-Dist": requires_dist,
    }
    if requires_python is not None:
        metadata_updates["Requires-Python"] = requires_python

    wheel_builder = make_wheel(
        name=name,
        version=version,
        wheel_metadata_updates={"Tag": ["py2-none-any", "py3-none-any"]},
        metadata_updates=metadata_updates,
        extra_metadata_files={"top_level.txt": name},
        extra_files=extra_files,
        # Have an empty RECORD because we don't want to be checking hashes.
        record="",
    )
    wheel_builder.save_to(archive_path)

    return archive_path


def create_basic_sdist_for_package(script, name, version, extra_files=None):
    files = {
        "setup.py": """
            from setuptools import find_packages, setup
            setup(name={name!r}, version={version!r})
        """,
    }

    # Some useful shorthands
    archive_name = "{name}-{version}.tar.gz".format(name=name, version=version)

    # Replace key-values with formatted values
    for key, value in list(files.items()):
        del files[key]
        key = key.format(name=name)
        files[key] = textwrap.dedent(value).format(name=name, version=version).strip()

    # Add new files after formatting
    if extra_files:
        files.update(extra_files)

    for fname in files:
        path = script.temp_path / fname
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(files[fname].encode("utf-8"))

    retval = script.scratch_path / archive_name
    generated = shutil.make_archive(
        retval,
        "gztar",
        root_dir=script.temp_path,
        base_dir=os.curdir,
    )
    shutil.move(generated, retval)

    shutil.rmtree(script.temp_path)
    script.temp_path.mkdir()

    return retval


def need_executable(name, check_cmd):
    def wrapper(fn):
        try:
            subprocess.check_output(check_cmd)
        except (OSError, subprocess.CalledProcessError):
            return pytest.mark.skip(reason=f"{name} is not available")(fn)
        return fn

    return wrapper


def is_bzr_installed():
    try:
        subprocess.check_output(("bzr", "version", "--short"))
    except OSError:
        return False
    return True


def is_svn_installed():
    try:
        subprocess.check_output(("svn", "--version"))
    except OSError:
        return False
    return True


def need_bzr(fn):
    return pytest.mark.bzr(need_executable("Bazaar", ("bzr", "version", "--short"))(fn))


def need_svn(fn):
    return pytest.mark.svn(
        need_executable("Subversion", ("svn", "--version"))(
            need_executable("Subversion Admin", ("svnadmin", "--version"))(fn)
        )
    )


def need_mercurial(fn):
    return pytest.mark.mercurial(need_executable("Mercurial", ("hg", "version"))(fn))
