"""Helpers for release automation.

These are written according to the order they are called in.
"""

import io
import os
import subprocess
from typing import List, Optional, Set

from nox.sessions import Session


def get_version_from_arguments(arguments: List[str]) -> Optional[str]:
    """Checks the arguments passed to `nox -s release`.

    If there is only 1 argument that looks like a pip version, returns that.
    Otherwise, returns None.
    """
    if len(arguments) != 1:
        return None

    version = arguments[0]

    parts = version.split('.')
    if not 2 <= len(parts) <= 3:
        # Not of the form: YY.N or YY.N.P
        return None

    if not all(part.isdigit() for part in parts):
        # Not all segments are integers.
        return None

    # All is good.
    return version


def modified_files_in_git(*args: str) -> int:
    return subprocess.run(
        ["git", "diff", "--no-patch", "--exit-code", *args],
        capture_output=True,
    ).returncode


def get_author_list() -> List[str]:
    """Get the list of authors from Git commits.
    """
    # subprocess because session.run doesn't give us stdout
    result = subprocess.run(
        ["git", "log", "--use-mailmap", "--format=%aN <%aE>"],
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
    with io.open(filename, "w", encoding="utf-8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


def commit_file(session: Session, filename: str, *, message: str) -> None:
    session.run("git", "add", filename, external=True, silent=True)
    session.run("git", "commit", "-m", message, external=True, silent=True)


def generate_news(session: Session, version: str) -> None:
    session.install("towncrier")
    session.run("towncrier", "--yes", "--version", version, silent=True)


def update_version_file(version: str, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('__version__ = "{}"\n'.format(version))


def create_git_tag(session: Session, tag_name: str, *, message: str) -> None:
    session.run(
        "git", "tag", "-m", message, tag_name, external=True, silent=True,
    )


def get_next_development_version(version: str) -> str:
    major, minor, *_ = map(int, version.split("."))

    # We have at most 4 releases, starting with 0. Once we reach 3, we'd want
    # to roll-over to the next year's release numbers.
    if minor == 3:
        major += 1
        minor = 0
    else:
        minor += 1

    return f"{major}.{minor}.dev0"


def have_files_in_folder(folder_name: str) -> bool:
    if not os.path.exists(folder_name):
        return False
    return bool(os.listdir(folder_name))
