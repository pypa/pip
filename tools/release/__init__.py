"""Helpers for release automation.

These are written according to the order they are called in.
"""

import contextlib
import os
import pathlib
import subprocess
import tempfile
from typing import Iterator, List, Optional, Set

from nox.sessions import Session


def get_version_from_arguments(session: Session) -> Optional[str]:
    """Checks the arguments passed to `nox -s release`.

    If there is only 1 argument that looks like a pip version, returns that.
    Otherwise, returns None.
    """
    if len(session.posargs) != 1:
        return None
    version = session.posargs[0]

    # We delegate to a script here, so that it can depend on packaging.
    session.install("packaging")
    cmd = [
        os.path.join(session.bin, "python"),
        "tools/release/check_version.py",
        version,
    ]
    not_ok = subprocess.run(cmd).returncode
    if not_ok:
        return None

    # All is good.
    return version


def modified_files_in_git(*args: str) -> int:
    return subprocess.run(
        ["git", "diff", "--no-patch", "--exit-code", *args],
        capture_output=True,
    ).returncode


def get_author_list() -> List[str]:
    """Get the list of authors from Git commits."""
    # subprocess because session.run doesn't give us stdout
    # only use names in list of Authors
    result = subprocess.run(
        ["git", "log", "--use-mailmap", "--format=%aN"],
        capture_output=True,
        encoding="utf-8",
    )

    # Create a unique list.
    authors = []
    seen_authors: Set[str] = set()
    for author in result.stdout.splitlines():
        author = author.strip()
        if author.lower() not in seen_authors:
            seen_authors.add(author.lower())
            authors.append(author)

    # Sort our list of Authors by their case insensitive name
    return sorted(authors, key=lambda x: x.lower())


def generate_authors(filename: str) -> None:
    # Get our list of authors
    authors = get_author_list()

    # Write our authors to the AUTHORS file
    with open(filename, "w", encoding="utf-8") as fp:
        fp.write("\n".join(authors))
        fp.write("\n")


def commit_file(session: Session, filename: str, *, message: str) -> None:
    session.run("git", "add", filename, external=True, silent=True)
    session.run("git", "commit", "-m", message, external=True, silent=True)


def generate_news(session: Session, version: str) -> None:
    session.install("towncrier")
    session.run("towncrier", "--yes", "--version", version, silent=True)


def update_version_file(version: str, filepath: str) -> None:
    with open(filepath, encoding="utf-8") as f:
        content = list(f)

    file_modified = False
    with open(filepath, "w", encoding="utf-8") as f:
        for line in content:
            if line.startswith("__version__ ="):
                f.write(f'__version__ = "{version}"\n')
                file_modified = True
            else:
                f.write(line)

    assert file_modified, f"Version file {filepath} did not get modified"


def create_git_tag(session: Session, tag_name: str, *, message: str) -> None:
    session.run(
        # fmt: off
        "git", "tag", "-m", message, tag_name,
        # fmt: on
        external=True,
        silent=True,
    )


def get_next_development_version(version: str) -> str:
    is_beta = "b" in version.lower()

    parts = version.split(".")
    s_major, s_minor, *_ = parts

    # We only permit betas.
    if is_beta:
        s_minor, _, s_dev_number = s_minor.partition("b")
    else:
        s_dev_number = "0"

    major, minor = map(int, [s_major, s_minor])

    # Increase minor version number if we're not releasing a beta.
    if not is_beta:
        # We have at most 4 releases, starting with 0. Once we reach 3, we'd
        # want to roll-over to the next year's release numbers.
        if minor == 3:
            major += 1
            minor = 0
        else:
            minor += 1

    return f"{major}.{minor}.dev" + s_dev_number


def have_files_in_folder(folder_name: str) -> bool:
    if not os.path.exists(folder_name):
        return False
    return bool(os.listdir(folder_name))


@contextlib.contextmanager
def workdir(
    nox_session: Session,
    dir_path: pathlib.Path,
) -> Iterator[pathlib.Path]:
    """Temporarily chdir when entering CM and chdir back on exit."""
    orig_dir = pathlib.Path.cwd()

    nox_session.chdir(dir_path)
    try:
        yield dir_path
    finally:
        nox_session.chdir(orig_dir)


@contextlib.contextmanager
def isolated_temporary_checkout(
    nox_session: Session,
    target_ref: str,
) -> Iterator[pathlib.Path]:
    """Make a clean checkout of a given version in tmp dir."""
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_dir = pathlib.Path(tmp_dir_path)
        git_checkout_dir = tmp_dir / f"pip-build-{target_ref}"
        nox_session.run(
            # fmt: off
            "git", "clone",
            "--depth", "1",
            "--config", "core.autocrlf=false",
            "--branch", str(target_ref),
            "--",
            ".", str(git_checkout_dir),
            # fmt: on
            external=True,
            silent=True,
        )

        yield git_checkout_dir


def get_git_untracked_files() -> Iterator[str]:
    """List all local file paths that aren't tracked by Git."""
    git_ls_files_cmd = (
        # fmt: off
        "git", "ls-files",
        "--ignored", "--exclude-standard",
        "--others", "--", ".",
        # fmt: on
    )
    # session.run doesn't seem to return any output:
    ls_files_out = subprocess.check_output(git_ls_files_cmd, text=True)
    for file_name in ls_files_out.splitlines():
        if file_name.strip():  # it's useless if empty
            continue

        yield file_name
