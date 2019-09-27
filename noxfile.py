"""Automation using nox.
"""

import io
import os
import shutil
import subprocess

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint"]

LOCATIONS = {
    "common-wheels": "tests/data/common_wheels",
    "protected-pip": "tools/tox_pip.py",
}
REQUIREMENTS = {
    "tests": "tools/requirements/tests.txt",
    "common-wheels": "tools/requirements/tests-common_wheels.txt",
}


def get_author_list():
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
    seen_authors = set()
    for author in result.stdout.splitlines():
        author = author.strip()
        if author.lower() not in seen_authors:
            seen_authors.add(author.lower())
            authors.append(author)

    # Sort our list of Authors by their case insensitive name
    return sorted(authors, key=lambda x: x.lower())


def protected_pip(*arguments):
    """Get arguments for session.run, that use a "protected" pip.
    """
    return ("python", LOCATIONS["protected-pip"]) + arguments


def should_update_common_wheels():
    # If the cache hasn't been created, create it.
    if not os.path.exists(LOCATIONS["common-wheels"]):
        return True

    # If the requirements was updated after cache, we'll repopulate it.
    cache_last_populated_at = os.path.getmtime(LOCATIONS["common-wheels"])
    requirements_updated_at = os.path.getmtime(REQUIREMENTS["common-wheels"])
    need_to_repopulate = requirements_updated_at > cache_last_populated_at

    # Clear the stale cache.
    if need_to_repopulate:
        shutil.remove(LOCATIONS["common-wheels"], ignore_errors=True)

    return need_to_repopulate


# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------
@nox.session(python=["2.7", "3.5", "3.6", "3.7", "pypy"])
def test(session):
    # Get the common wheels.
    if should_update_common_wheels():
        session.run(*protected_pip(
            "wheel",
            "-w", LOCATIONS["common-wheels"],
            "-r", REQUIREMENTS["common-wheels"],
        ))

    # Install sources and dependencies
    session.run(*protected_pip("install", "."))
    session.run(*protected_pip("install", "-r", REQUIREMENTS["tests"]))

    # Run the tests
    session.run("pytest", *session.posargs, env={"LC_CTYPE": "en_US.UTF-8"})


@nox.session
def docs(session):
    session.install(".")
    session.install("-r", REQUIREMENTS["docs"])

    def get_sphinx_build_command(kind):
        return [
            "sphinx-build",
            "-W",
            "-c", "docs/html",
            "-d", "docs/build/doctrees/" + kind,
            "-b", kind,
            "docs/" + kind,
            "docs/build/" + kind,
        ]

    session.run(*get_sphinx_build_command("html"))
    session.run(*get_sphinx_build_command("man"))


@nox.session
def lint(session):
    session.install("pre-commit")

    if session.posargs:
        args = session.posargs + ["--all-files"]
    else:
        args = ["--all-files", "--show-diff-on-failure"]

    session.run("pre-commit", "run", *args)


# -----------------------------------------------------------------------------
# Release Commands
# -----------------------------------------------------------------------------
@nox.session(python=False)
def generate_authors(session):
    # Get our list of authors
    session.log("Collecting author names")
    authors = get_author_list()

    # Write our authors to the AUTHORS file
    session.log("Writing AUTHORS")
    with io.open("AUTHORS.txt", "w", encoding="utf-8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


@nox.session
def generate_news(session):
    session.log("Generating NEWS")
    session.install("towncrier")

    # You can pass 2 possible arguments: --draft, --yes
    session.run("towncrier", *session.posargs)
