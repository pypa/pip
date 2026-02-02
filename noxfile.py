"""Automation using nox."""

import argparse
import glob
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import nox

# fmt: off
sys.path.append(".")
from tools import release  # isort:skip
sys.path.pop()
# fmt: on

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint"]
nox.needs_version = ">=2024.03.02"  # for session.run_install()

LOCATIONS = {
    "common-wheels": "tests/data/common_wheels",
    "protected-pip": "tools/protected_pip.py",
}

AUTHORS_FILE = "AUTHORS.txt"
VERSION_FILE = "src/pip/__init__.py"


def run_with_protected_pip(session: nox.Session, *arguments: str) -> None:
    """Do a session.run("pip", *arguments), using a "protected" pip.

    This invokes a wrapper script, that forwards calls to original virtualenv
    (stable) version, and not the code being tested. This ensures pip being
    used is not the code being tested.
    """
    env = {"VIRTUAL_ENV": session.virtualenv.location}

    command = ("python", LOCATIONS["protected-pip"]) + arguments
    # By using run_install(), these installation steps can be skipped when -R
    # or --no-install is passed.
    session.run_install(*command, env=env, silent=True)


def should_update_common_wheels() -> bool:
    # If the cache hasn't been created, create it.
    if not os.path.exists(LOCATIONS["common-wheels"]):
        return True

    # If the pyproject.toml was updated after cache, we'll repopulate it.
    cache_last_populated_at = os.path.getmtime(LOCATIONS["common-wheels"])
    pyproject_updated_at = os.path.getmtime("pyproject.toml")
    need_to_repopulate = pyproject_updated_at > cache_last_populated_at

    # Clear the stale cache.
    if need_to_repopulate:
        shutil.rmtree(LOCATIONS["common-wheels"], ignore_errors=True)

    return need_to_repopulate


# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------
@nox.session(python=["3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "pypy3"])
def test(session: nox.Session) -> None:
    # Get the common wheels.
    if should_update_common_wheels():
        # fmt: off
        run_with_protected_pip(
            session,
            "wheel",
            "-w", LOCATIONS["common-wheels"],
            "--group", "test-common-wheels",
        )
        # fmt: on
    else:
        msg = f"Reusing existing common-wheels at {LOCATIONS['common-wheels']}."
        session.log(msg)

    # Build source distribution
    # HACK: we want to skip building and installing pip when nox's --no-install
    # flag is given (to save time when running tests back to back with different
    # arguments), but unfortunately nox does not expose this configuration state
    # yet. https://github.com/wntrblm/nox/issues/710
    no_install = "-R" in sys.argv or "--no-install" in sys.argv
    sdist_dir = os.path.join(session.virtualenv.location, "sdist")
    if not no_install and os.path.exists(sdist_dir):
        shutil.rmtree(sdist_dir, ignore_errors=True)

    run_with_protected_pip(session, "install", "build")
    # build uses the pip present in the outer environment (aka the nox environment)
    # as an optimization. This will crash if the last test run installed a broken
    # pip, so uninstall pip to force build to provision a known good version of pip.
    run_with_protected_pip(session, "uninstall", "pip", "-y")
    # fmt: off
    session.run_install(
        "python", "-I", "-m", "build", "--sdist", "--outdir", sdist_dir,
        silent=True,
    )
    # fmt: on

    generated_files = os.listdir(sdist_dir)
    assert len(generated_files) == 1
    generated_sdist = os.path.join(sdist_dir, generated_files[0])

    # Install source distribution
    run_with_protected_pip(session, "install", generated_sdist)

    # Install test dependencies
    run_with_protected_pip(session, "install", "--group", "test")

    # Parallelize tests as much as possible, by default.
    arguments = session.posargs or ["-n", "auto"]

    # Run the tests
    #   LC_CTYPE is set to get UTF-8 output inside of the subprocesses that our
    #   tests use.
    session.run(
        "pytest",
        *arguments,
        env={
            "LC_CTYPE": "en_US.UTF-8",
        },
    )


@nox.session
def docs(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("--group", "docs")

    def get_sphinx_build_command(kind: str) -> list[str]:
        # Having the conf.py in the docs/html is weird but needed because we
        # can not use a different configuration directory vs source directory
        # on RTD currently. So, we'll pass "-c docs/html" here.
        # See https://github.com/rtfd/readthedocs.org/issues/1543.
        # fmt: off
        return [
            "sphinx-build",
            "--keep-going",
            "--tag", kind,
            "-W",
            "-c", "docs/html",  # see note above
            "-d", "docs/build/doctrees/" + kind,
            "-b", kind,
            "--jobs", "auto",
            "docs/" + kind,
            "docs/build/" + kind,
        ]
        # fmt: on

    shutil.rmtree("docs/build", ignore_errors=True)
    session.run(*get_sphinx_build_command("html"))
    session.run(*get_sphinx_build_command("man"))


@nox.session(name="docs-live")
def docs_live(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("--group", "docs", "sphinx-autobuild")

    session.run(
        "sphinx-autobuild",
        "-d=docs/build/doctrees/livehtml",
        "-b=dirhtml",
        "docs/html",
        "docs/build/livehtml",
        "--jobs=auto",
        *session.posargs,
    )


@nox.session
def lint(session: nox.Session) -> None:
    session.install("pre-commit")

    if session.posargs:
        args = session.posargs + ["--all-files"]
    else:
        args = ["--all-files", "--show-diff-on-failure"]

    session.run("pre-commit", "run", *args)


# NOTE: This session will COMMIT upgrades to vendored libraries.
# You should therefore not run it directly against `main`. If you
# do (assuming you started with a clean main), you can run:
#
# git checkout -b vendoring-updates
# git checkout main
# git reset --hard origin/main
@nox.session
def vendoring(session: nox.Session) -> None:
    # Ensure that the session Python is running 3.10+
    # so that truststore can be installed correctly.
    session.run(
        "python", "-c", "import sys; sys.exit(1 if sys.version_info < (3, 10) else 0)"
    )

    parser = argparse.ArgumentParser(prog="nox -s vendoring")
    parser.add_argument("--upgrade-all", action="store_true")
    parser.add_argument("--upgrade", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    args = parser.parse_args(session.posargs)

    session.install("vendoring~=1.2.0")

    if not (args.upgrade or args.upgrade_all):
        session.run("vendoring", "sync", "-v")
        return

    def pinned_requirements(path: Path) -> Iterator[tuple[str, str]]:
        for line in path.read_text().splitlines(keepends=False):
            one, sep, two = line.partition("==")
            if not sep:
                continue
            name = one.strip()
            version = two.split("#", 1)[0].strip()
            if name and version:
                yield name, version

    vendor_txt = Path("src/pip/_vendor/vendor.txt")
    for name, old_version in pinned_requirements(vendor_txt):
        if name in args.skip:
            continue
        if args.upgrade and name not in args.upgrade:
            continue

        # update requirements.txt
        session.run("vendoring", "update", ".", name)

        # get the updated version
        new_version = old_version
        for inner_name, inner_version in pinned_requirements(vendor_txt):
            if inner_name == name:
                # this is a dedicated assignment, to make lint happy
                new_version = inner_version
                break
        else:
            session.error(f"Could not find {name} in {vendor_txt}")

        # check if the version changed.
        if new_version == old_version:
            continue  # no change, nothing more to do here.

        # synchronize the contents
        session.run("vendoring", "sync", ".")

        # Determine the correct message
        message = f"Upgrade {name} to {new_version}"

        # Write our news fragment
        news_file = Path("news") / (name + ".vendor.rst")
        news_file.write_text(message + "\n")  # "\n" appeases end-of-line-fixer

        # Commit the changes
        release.commit_file(session, ".", message=message)


@nox.session
def coverage(session: nox.Session) -> None:
    # Install source distribution
    run_with_protected_pip(session, "install", ".")

    # Install test dependencies
    run_with_protected_pip(session, "install", "--group", "tests")

    if not os.path.exists(".coverage-output"):
        os.mkdir(".coverage-output")
    session.run(
        "pytest",
        "--cov=pip",
        "--cov-config=./setup.cfg",
        *session.posargs,
        env={
            "COVERAGE_OUTPUT_DIR": "./.coverage-output",
            "COVERAGE_PROCESS_START": os.fsdecode(Path("setup.cfg").resolve()),
        },
    )


# -----------------------------------------------------------------------------
# Release Commands
# -----------------------------------------------------------------------------
@nox.session(name="prepare-release")
def prepare_release(session: nox.Session) -> None:
    version = release.get_version_from_arguments(session)
    if not version:
        session.error("Usage: nox -s prepare-release -- <version>")

    session.log("# Ensure nothing is staged")
    if release.modified_files_in_git("--staged"):
        session.error("There are files staged in git")

    session.log(f"# Updating {AUTHORS_FILE}")
    release.generate_authors(AUTHORS_FILE)
    if release.modified_files_in_git():
        release.commit_file(session, AUTHORS_FILE, message=f"Update {AUTHORS_FILE}")
    else:
        session.log(f"# No changes to {AUTHORS_FILE}")

    session.log("# Generating NEWS")
    release.generate_news(session, version)
    if sys.stdin.isatty():
        input(
            "Please review the NEWS file, make necessary edits, and stage them.\n"
            "Press Enter to continue..."
        )

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
def build_release(session: nox.Session) -> None:
    version = release.get_version_from_arguments(session)
    if not version:
        session.error("Usage: nox -s build-release -- YY.N[.P]")

    session.log("# Ensure no files in dist/")
    if release.have_files_in_folder("dist"):
        session.error(
            "There are files in dist/. Remove them and try again. "
            "You can use `git clean -fxdi -- dist` command to do this"
        )

    session.log("# Install dependencies")
    session.install("twine")

    with release.isolated_temporary_checkout(session, version) as build_dir:
        session.log(
            "# Start the build in an isolated, "
            f"temporary Git checkout at {build_dir!s}",
        )
        with release.workdir(session, build_dir):
            tmp_dists = build_dists(session)

        tmp_dist_paths = (build_dir / p for p in tmp_dists)
        session.log(f"# Copying dists from {build_dir}")
        os.makedirs("dist", exist_ok=True)
        for dist, final in zip(tmp_dist_paths, tmp_dists):
            session.log(f"# Copying {dist} to {final}")
            shutil.copy(dist, final)


def build_dists(session: nox.Session) -> list[str]:
    """Return dists with valid metadata."""
    session.log(
        "# Check if there's any Git-untracked files before building the wheel",
    )

    has_forbidden_git_untracked_files = any(
        # Don't report the environment this session is running in
        not untracked_file.startswith(".nox/build-release/")
        for untracked_file in release.get_git_untracked_files()
    )
    if has_forbidden_git_untracked_files:
        session.error(
            "There are untracked files in the working directory. "
            "Remove them and try again",
        )

    session.log("# Build distributions")
    session.run("python", "build-project/build-project.py", silent=True)
    produced_dists = glob.glob("dist/*")

    session.log(f"# Verify distributions: {', '.join(produced_dists)}")
    session.run("twine", "check", "--strict", *produced_dists, silent=True)

    return produced_dists


@nox.session(name="upload-release")
def upload_release(session: nox.Session) -> None:
    version = release.get_version_from_arguments(session)
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
    distfile_names = (os.path.basename(fn) for fn in distribution_files)
    expected_distribution_files = [
        f"pip-{version}-py3-none-any.whl",
        f"pip-{version}.tar.gz",
    ]
    if sorted(distfile_names) != sorted(expected_distribution_files):
        session.error(f"Distribution files do not seem to be for {version} release.")

    session.log("# Upload distributions")
    session.run("twine", "upload", *distribution_files)
