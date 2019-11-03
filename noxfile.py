"""Automation using nox.
"""

# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

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

AUTHORS_FILE = "AUTHORS.txt"
VERSION_FILE = "src/pip/__init__.py"


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


def run_with_protected_pip(session, *arguments):
    """Do a session.run("pip", *arguments), using a "protected" pip.

    This invokes a wrapper script, that forwards calls to original virtualenv
    (stable) version, and not the code being tested. This ensures pip being
    used is not the code being tested.
    """
    env = {"VIRTUAL_ENV": session.virtualenv.location}

    command = ("python", LOCATIONS["protected-pip"]) + arguments
    kwargs = {"env": env, "silent": True}
    session.run(*command, **kwargs)


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
        shutil.rmtree(LOCATIONS["common-wheels"], ignore_errors=True)

    return need_to_repopulate


def update_version_file(new_version):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write('__version__ = "{}"\n'.format(new_version))


# -----------------------------------------------------------------------------
# Development Commands
#   These are currently prototypes to evaluate whether we want to switch over
#   completely to nox for all our automation. Contributors should prefer using
#   `tox -e ...` until this note is removed.
# -----------------------------------------------------------------------------
@nox.session(python=["2.7", "3.5", "3.6", "3.7", "pypy"])
def test(session):
    # Get the common wheels.
    if should_update_common_wheels():
        run_with_protected_pip(
            session,
            "wheel",
            "-w", LOCATIONS["common-wheels"],
            "-r", REQUIREMENTS["common-wheels"],
        )
    else:
        msg = (
            "Re-using existing common-wheels at {}."
            .format(LOCATIONS["common-wheels"])
        )
        session.log(msg)

    # Build source distribution
    sdist_dir = os.path.join(session.virtualenv.location, "sdist")
    session.run(
        "python", "setup.py", "sdist",
        "--formats=zip", "--dist-dir", sdist_dir,
        silent=True,
    )
    generated_files = os.listdir(sdist_dir)
    assert len(generated_files) == 1
    generated_sdist = os.path.join(sdist_dir, generated_files[0])

    # Install source distribution
    run_with_protected_pip(session, "install", generated_sdist)

    # Install test dependencies
    run_with_protected_pip(session, "install", "-r", REQUIREMENTS["tests"])

    # Parallelize tests as much as possible, by default.
    arguments = session.posargs or ["-n", "auto"]

    # Run the tests
    #   LC_CTYPE is set to get UTF-8 output inside of the subprocesses that our
    #   tests use.
    session.run("pytest", *arguments, env={"LC_CTYPE": "en_US.UTF-8"})


@nox.session
def docs(session):
    session.install(".")
    session.install("-r", REQUIREMENTS["docs"])

    def get_sphinx_build_command(kind):
        # Having the conf.py in the docs/html is weird but needed because we
        # can not use a different configuration directory vs source directory
        # on RTD currently. So, we'll pass "-c docs/html" here.
        # See https://github.com/rtfd/readthedocs.org/issues/1543.
        return [
            "sphinx-build",
            "-W",
            "-c", "docs/html",  # see note above
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
    with io.open(AUTHORS_FILE, "w", encoding="utf-8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


@nox.session
def generate_news(session):
    session.log("Generating NEWS")
    session.install("towncrier")

    # You can pass 2 possible arguments: --draft, --yes
    session.run("towncrier", *session.posargs)


@nox.session
def release(session):
    assert len(session.posargs) == 1, "A version number is expected"
    new_version = session.posargs[0]
    parts = new_version.split('.')
    # Expect YY.N or YY.N.P
    assert 2 <= len(parts) <= 3, parts
    # Only integers
    parts = list(map(int, parts))
    session.log("Generating commits for version {}".format(new_version))

    session.log("Checking that nothing is staged")
    # Non-zero exit code means that something is already staged
    session.run("git", "diff", "--staged", "--exit-code", external=True)

    session.log(f"Updating {AUTHORS_FILE}")
    generate_authors(session)
    if subprocess.run(["git", "diff", "--exit-code"]).returncode:
        session.run("git", "add", AUTHORS_FILE, external=True)
        session.run(
            "git", "commit", "-m", f"Updating {AUTHORS_FILE}",
            external=True,
        )
    else:
        session.log(f"No update needed for {AUTHORS_FILE}")

    session.log("Generating NEWS")
    session.install("towncrier")
    session.run("towncrier", "--yes", "--version", new_version)

    session.log("Updating version")
    update_version_file(new_version)
    session.run("git", "add", VERSION_FILE, external=True)
    session.run("git", "commit", "-m", f"Release {new_version}", external=True)

    session.log("Tagging release")
    session.run(
        "git", "tag", "-m", f"Release {new_version}", new_version,
        external=True,
    )

    next_dev_version = f"{parts[0]}.{parts[1] + 1}.dev0"
    update_version_file(next_dev_version)
    session.run("git", "add", VERSION_FILE, external=True)
    session.run("git", "commit", "-m", "Back to development", external=True)
