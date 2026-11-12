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
nox.needs_version = ">=2024.04.15"  # for nox.project.load_toml()

LOCATIONS = {
    "common-wheels": "tests/data/common_wheels",
    "protected-pip": "tools/protected_pip.py",
}

AUTHORS_FILE = "AUTHORS.txt"
VERSION_FILE = "src/pip/__init__.py"
DEV_LOCK = "pylock.dev.toml"
DEPENDENCY_FILE = (
    "pyproject.toml" if os.environ.get("PIP_NOX_USE_LOCK") == "0" else DEV_LOCK
)


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


def dependency_group_arguments(*groups: str) -> list[str]:
    """Select locked groups, or project requirements for an unlocked run."""
    arguments: list[str] = []
    for group in groups:
        if DEPENDENCY_FILE == "pyproject.toml" and group == "build":
            # Nab derives this group from the project's build requirements.
            project = nox.project.load_toml("pyproject.toml")
            arguments.extend(project["build-system"]["requires"])
        else:
            arguments.extend(("--group", f"{DEPENDENCY_FILE}:{group}"))
    return arguments


def install_groups(session: nox.Session, *groups: str) -> None:
    """Install the session's dependency groups with the protected installer."""
    run_with_protected_pip(session, "install", *dependency_group_arguments(*groups))


def should_update_common_wheels(session: nox.Session) -> bool:
    """Determine if the common wheels cache needs to be updated.

    The cache is invalidated if:
    1. It doesn't exist yet
    2. The dependency source changed, or its inputs were modified
    3. The cached wheels cannot satisfy the current Python version's requirements
    """
    # If the cache hasn't been created, create it.
    if not os.path.exists(LOCATIONS["common-wheels"]):
        return True

    cache_last_populated_at = os.path.getmtime(LOCATIONS["common-wheels"])
    inputs_updated_at = max(
        os.path.getmtime("pyproject.toml"), os.path.getmtime(DEPENDENCY_FILE)
    )
    source_file = Path(LOCATIONS["common-wheels"], ".dependency-source")
    need_to_repopulate = (
        not source_file.exists()
        or source_file.read_text() != DEPENDENCY_FILE
        or inputs_updated_at > cache_last_populated_at
    )

    if not need_to_repopulate:
        # Check the project group against local wheels. Pylock artifact URLs
        # would fetch distributions instead of testing this directory.
        result = session.run(
            "python",
            LOCATIONS["protected-pip"],
            "install",
            "--dry-run",
            "--ignore-installed",
            "--no-index",
            "--find-links",
            LOCATIONS["common-wheels"],
            "--group",
            "test-common-wheels",
            env={"VIRTUAL_ENV": session.virtualenv.location},
            silent=True,
            success_codes=[0, 1],  # Accept both success and failure and check result
        )

        # Result is the stdout of the pip install command.
        if result is None or "Would install" not in result:
            session.log(
                "Regenerating common wheels as cached wheels "
                "cannot satisfy test-common-wheels"
            )
            need_to_repopulate = True

    # Clear the stale cache.
    if need_to_repopulate:
        shutil.rmtree(LOCATIONS["common-wheels"], ignore_errors=True)

    return need_to_repopulate


def get_common_wheels(session: nox.Session) -> None:
    """Build the common wheels needed by tests."""
    if should_update_common_wheels(session):
        # fmt: off
        run_with_protected_pip(
            session,
            "wheel",
            "-w", LOCATIONS["common-wheels"],
            *dependency_group_arguments("test-common-wheels"),
        )
        # fmt: on
        Path(LOCATIONS["common-wheels"], ".dependency-source").write_text(
            DEPENDENCY_FILE
        )
    else:
        msg = f"Reusing existing common-wheels at {LOCATIONS['common-wheels']}."
        session.log(msg)


# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------
@nox.session(venv_backend="venv")
def lock(session: nox.Session) -> None:
    """Update development and script locks with a pinned resolver."""
    session.install("nab==0.0.29")

    session.run("nab", "lock", "--all-groups", "--output", DEV_LOCK, *session.posargs)

    # Use the environment declared by the redirects workflow.
    session.run(
        "nab",
        "lock",
        "--script",
        "tools/update-rtd-redirects.py",
        "--project-mode",
        "specific",
        "--project-environment-python",
        "3.11",
        "--project-environment-platform",
        "linux_x86_64",
        "--project-environment-implementation",
        "cpython",
        "--project-uploaded-prior-to",
        "P7D",
        "--project-dist-policy",
        "sdist-if-needed",
        "--project-build-policy",
        "never",
        *session.posargs,
    )


@nox.session(name="common-wheels")
def common_wheels(session: nox.Session) -> None:
    """Build the common wheels needed by tests."""
    get_common_wheels(session)


@nox.session(
    python=["3.10", "3.11", "3.12", "3.13", "3.14", "3.15", "3.14t", "3.15t", "pypy3"]
)
def test(session: nox.Session) -> None:
    if isinstance(session.python, str) and session.python.endswith("t"):
        session.env["PYTHON_GIL"] = "0"

    # Get the common wheels.
    get_common_wheels(session)

    # Build source distribution
    # HACK: we want to skip building and installing pip when nox's --no-install
    # flag is given (to save time when running tests back to back with different
    # arguments), but unfortunately nox does not expose this configuration state
    # yet. https://github.com/wntrblm/nox/issues/710
    no_install = "-R" in sys.argv or "--no-install" in sys.argv
    sdist_dir = os.path.join(session.virtualenv.location, "sdist")
    if not no_install and os.path.exists(sdist_dir):
        shutil.rmtree(sdist_dir, ignore_errors=True)

    install_groups(session, "test", "build")
    # Remove pip left by a previous run so the new sdist is always installed.
    run_with_protected_pip(session, "uninstall", "pip", "-y")
    # fmt: off
    session.run_install(
        "python", "-I", "-m", "build", "--no-isolation", "--sdist",
        "--outdir", sdist_dir,
        silent=True,
    )
    # fmt: on

    generated_files = os.listdir(sdist_dir)
    assert len(generated_files) == 1
    generated_sdist = os.path.join(sdist_dir, generated_files[0])

    # Install source distribution
    run_with_protected_pip(session, "install", "--no-build-isolation", generated_sdist)

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
def typecheck(session: nox.Session) -> None:
    """Run mypy over the pip source, tests, and tooling.

    The "typecheck" dependency group installs the runtime and test
    dependencies alongside a few type stub packages (e.g. types-setuptools),
    so mypy can import and resolve their types directly.

    Vendored dependencies such as requests and urllib3 now ship inline types in
    their vendored source, so mypy resolves them straight from src/pip/_vendor.
    Type errors within the vendored packages themselves are an upstream concern
    and are ignored via tests/typing/pyproject.toml.
    """
    install_groups(session, "typecheck")

    mypy_cmd = [
        "mypy",
        "--config-file=tests/typing/pyproject.toml",
    ]
    if session.posargs:
        # Allow passing specific files/directories to be checked.
        mypy_cmd.extend(session.posargs)
    else:
        # Otherwise, run against all important files.
        mypy_cmd.extend(
            [
                "src/pip",
                "tests",
                "tools",
                "noxfile.py",
            ]
        )
    session.run(*mypy_cmd)


@nox.session
def docs(session: nox.Session) -> None:
    install_groups(session, "docs", "build")
    run_with_protected_pip(
        session, "install", "--no-deps", "--no-build-isolation", "-e", "."
    )

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
    install_groups(session, "docs-live", "build")
    run_with_protected_pip(
        session, "install", "--no-deps", "--no-build-isolation", "-e", "."
    )

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
    install_groups(session, "lint")

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
    parser = argparse.ArgumentParser(prog="nox -s vendoring")
    parser.add_argument("--upgrade-all", action="store_true")
    parser.add_argument("--upgrade", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    args = parser.parse_args(session.posargs)

    session.run(
        "python",
        "-c",
        "import sys; sys.exit(0 if sys.version_info >= (3, 11) else "
        "'vendoring requires Python 3.11 or newer')",
        silent=True,
    )
    install_groups(session, "vendoring")

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
        session.run("vendoring", "update", name)

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
        session.run("vendoring", "sync")

        # Determine the correct message
        message = f"Upgrade {name} to {new_version}"

        # Write our news fragment
        news_file = Path("news") / (name + ".vendor.rst")
        news_file.write_text(message + "\n")  # "\n" appeases end-of-line-fixer

        # Commit the changes
        release.commit_file(session, ".", message=message)


@nox.session
def coverage(session: nox.Session) -> None:
    get_common_wheels(session)

    install_groups(session, "test", "build")
    run_with_protected_pip(session, "install", "--no-deps", "--no-build-isolation", ".")

    coverage_output_dir = Path(".coverage-output").resolve()
    coverage_output_dir.mkdir(exist_ok=True)

    session.run(
        "pytest",
        "--cov=pip",
        "--cov-config=pyproject.toml",
        *session.posargs,
        env={
            "COVERAGE_OUTPUT_DIR": os.fsdecode(coverage_output_dir),
            "COVERAGE_PROCESS_START": os.fsdecode(Path("pyproject.toml").resolve()),
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

    install_groups(session, "prepare-release")

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

    install_groups(session, "build-release", "build")

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

    session.run("check-sdist", "--no-isolation", silent=True)

    session.log(f"# Verify distributions: {', '.join(produced_dists)}")
    session.run("twine", "check", "--strict", *produced_dists, silent=True)

    return produced_dists


@nox.session(name="upload-release")
def upload_release(session: nox.Session) -> None:
    version = release.get_version_from_arguments(session)
    if not version:
        session.error("Usage: nox -s upload-release -- YY.N[.P]")

    install_groups(session, "upload-release")

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
