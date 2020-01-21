"""Automation using nox.
"""

# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

import glob
import os
import shutil
import sys

import nox

sys.path.append(".")
from tools.automation import release  # isort:skip  # noqa
sys.path.pop()

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


# -----------------------------------------------------------------------------
# Development Commands
#   These are currently prototypes to evaluate whether we want to switch over
#   completely to nox for all our automation. Contributors should prefer using
#   `tox -e ...` until this note is removed.
# -----------------------------------------------------------------------------
@nox.session(python=["2.7", "3.5", "3.6", "3.7", "3.8", "pypy", "pypy3"])
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
    if os.path.exists(sdist_dir):
        shutil.rmtree(sdist_dir, ignore_errors=True)
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
@nox.session(name="prepare-release")
def prepare_release(session):
    version = release.get_version_from_arguments(session.posargs)
    if not version:
        session.error("Usage: nox -s prepare-release -- YY.N[.P]")

    session.log("# Ensure nothing is staged")
    if release.modified_files_in_git("--staged"):
        session.error("There are files staged in git")

    session.log(f"# Updating {AUTHORS_FILE}")
    release.generate_authors(AUTHORS_FILE)
    if release.modified_files_in_git():
        release.commit_file(
            session, AUTHORS_FILE, message=f"Update {AUTHORS_FILE}",
        )
    else:
        session.log(f"# No changes to {AUTHORS_FILE}")

    session.log("# Generating NEWS")
    release.generate_news(session, version)

    session.log(f"# Bumping for release {version}")
    release.update_version_file(version, VERSION_FILE)
    release.commit_file(session, VERSION_FILE, message="Bump for release")

    session.log("# Tagging release")
    release.create_git_tag(session, version, message=f"Release {version}")

    session.log("# Bumping for development")
    next_dev_version = release.get_next_development_version(version)
    release.update_version_file(next_dev_version, VERSION_FILE)
    release.commit_file(session, VERSION_FILE, message="Bump for development")


@nox.session(name="build-release")
def build_release(session):
    version = release.get_version_from_arguments(session.posargs)
    if not version:
        session.error("Usage: nox -s build-release -- YY.N[.P]")

    session.log("# Ensure no files in dist/")
    if release.have_files_in_folder("dist"):
        session.error("There are files in dist/. Remove them and try again")

    session.log("# Install dependencies")
    session.install("setuptools", "wheel", "twine")

    session.log("# Checkout the tag")
    session.run("git", "checkout", version, external=True, silent=True)

    session.log("# Wipe Git-untracked files before building the wheel")
    session.run("git", "clean", "-fxd", external=True, silent=True)

    session.log("# Build distributions")
    session.run("python", "setup.py", "sdist", "bdist_wheel", silent=True)

    session.log("# Verify distributions")
    session.run("twine", "check", *glob.glob("dist/*"), silent=True)

    session.log("# Checkout the master branch")
    session.run("git", "checkout", "master", external=True, silent=True)


@nox.session(name="upload-release")
def upload_release(session):
    version = release.get_version_from_arguments(session.posargs)
    if not version:
        session.error("Usage: nox -s upload-release -- YY.N[.P]")

    session.log("# Install dependencies")
    session.install("twine")

    distribution_files = glob.glob("dist/*")
    session.log(f"# Distribution files: {distribution_files}")

    # Sanity check: Make sure there's 2 distribution files.
    count = len(distribution_files)
    if count != 2:
        session.error(
            f"Expected 2 distribution files for upload, got {count}. "
            f"Remove dist/ and run 'nox -s build-release -- {version}'"
        )
    # Sanity check: Make sure the files are correctly named.
    expected_distribution_files = [
        f"dist/pip-{version}-py2.py3-none-any.whl",
        f"dist/pip-{version}.tar.gz",
    ]
    if sorted(distribution_files) != sorted(expected_distribution_files):
        session.error(
            f"Distribution files do not seem to be for {version} release."
        )

    session.log("# Upload distributions")
    session.run("twine", "upload", *distribution_files)
