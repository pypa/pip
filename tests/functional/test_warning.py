import os
import textwrap
from pathlib import Path

import pytest

from tests.lib import PipTestEnvironment, create_basic_sdist_for_package, git_commit


@pytest.fixture
def warnings_demo(tmpdir: Path) -> Path:
    demo = tmpdir.joinpath("warnings_demo.py")
    demo.write_text(textwrap.dedent("""
        from logging import basicConfig
        from pip._internal.utils import deprecation

        deprecation.install_warning_logger()
        basicConfig()

        deprecation.deprecated(reason="deprecated!", replacement=None, gone_in=None)
    """))
    return demo


def test_deprecation_warnings_are_correct(
    script: PipTestEnvironment, warnings_demo: Path
) -> None:
    script.environ["_PIP_TEST_ENV"] = ""
    result = script.run("python", os.fspath(warnings_demo), expect_stderr=True)
    expected = "WARNING:pip._internal.deprecations:DEPRECATION: deprecated!\n"
    assert result.stderr == expected


def test_deprecation_warnings_turn_into_errors_in_tests(
    script: PipTestEnvironment, warnings_demo: Path
) -> None:
    result = script.run(
        "python", os.fspath(warnings_demo), expect_error=True, expect_stderr=True
    )
    assert result.stderr.startswith("Traceback")
    expected = "utils.deprecation.PipDeprecationWarning: DEPRECATION: deprecated!\n"
    assert result.stderr.endswith(expected)


def test_deprecation_warnings_can_be_silenced(
    script: PipTestEnvironment, warnings_demo: Path
) -> None:
    script.environ["PYTHONWARNINGS"] = "ignore"
    script.environ["_PIP_TEST_ENV"] = ""
    result = script.run("python", os.fspath(warnings_demo))
    assert result.stderr == ""


@pytest.fixture
def warning_project(script: PipTestEnvironment) -> Path:
    """Create a backend that warns while preparing metadata."""
    script.temporary_multiline_file(
        "project/pyproject.toml",
        """\
        [build-system]
        requires = []
        build-backend = "backend"
        backend-path = ["."]
        """,
    )
    script.temporary_multiline_file(
        "project/backend.py",
        """\
        import warnings
        from pathlib import Path

        def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
            warnings.warn("backend warning [bold] from metadata hook", UserWarning)
            metadata = Path(metadata_directory) / "warning_demo-1.0.dist-info"
            metadata.mkdir()
            (metadata / "METADATA").write_text(
                "Metadata-Version: 2.1\\nName: warning-demo\\nVersion: 1.0\\n"
            )
            return metadata.name

        prepare_metadata_for_build_editable = prepare_metadata_for_build_wheel

        def build_editable(
            wheel_directory, config_settings=None, metadata_directory=None
        ):
            raise AssertionError("a dry run should not build a wheel")
        """,
    )
    return script.scratch_path / "project"


@pytest.mark.parametrize("source", ["directory", "editable", "sdist"])
@pytest.mark.parametrize(
    "verbosity", [(), ("-vv",), ("--quiet",)], ids=["normal", "verbose", "quiet"]
)
@pytest.mark.parametrize(
    "build_isolation", [False, True], ids=["no-isolation", "isolated"]
)
def test_build_backend_warnings(
    script: PipTestEnvironment,
    warning_project: Path,
    source: str,
    verbosity: tuple[str, ...],
    build_isolation: bool,
) -> None:
    requirement = warning_project
    if source == "sdist":
        requirement = create_basic_sdist_for_package(
            script,
            "warning_demo",
            "1.0",
            extra_files={
                name: (warning_project / name).read_text()
                for name in ("pyproject.toml", "backend.py")
            },
        )
    install_args = ["--editable"] if source == "editable" else []
    log_path = script.scratch_path / "pip.log"

    result = script.pip_install_local(
        *verbosity,
        "--dry-run",
        "--no-deps",
        "--log",
        str(log_path),
        *install_args,
        requirement,
        find_links=[],
        build_isolation=build_isolation,
        allow_stderr_warning=source != "sdist",
    )

    warning = "BuildBackendWarning: backend warning [bold] from metadata hook"
    assert warning in log_path.read_text()
    if source != "sdist":
        assert f"{warning_project / 'backend.py'}:5: {warning}" in result.stderr
    elif verbosity == ("-vv",):
        assert warning in result.stdout
        assert warning not in result.stderr
    else:
        assert warning not in result.stdout + result.stderr


@pytest.mark.git
@pytest.mark.parametrize("verbosity", [(), ("-vv",)], ids=["normal", "verbose"])
def test_build_backend_warnings_from_vcs(
    script: PipTestEnvironment, warning_project: Path, verbosity: tuple[str, ...]
) -> None:
    script.run("git", "init", "--quiet", cwd=warning_project)
    script.run("git", "add", ".", cwd=warning_project)
    git_commit(warning_project)
    log_path = script.scratch_path / "pip.log"

    result = script.pip_install_local(
        *verbosity,
        "--dry-run",
        "--no-deps",
        "--log",
        str(log_path),
        f"git+{warning_project.as_uri()}",
        find_links=[],
        build_isolation=True,
    )

    warning = "BuildBackendWarning: backend warning [bold] from metadata hook"
    assert warning in log_path.read_text()
    assert warning not in result.stderr
    if verbosity:
        assert warning in result.stdout
    else:
        assert warning not in result.stdout


def test_build_backend_warnings_can_be_silenced(
    script: PipTestEnvironment, warning_project: Path
) -> None:
    script.environ["PYTHONWARNINGS"] = "ignore::UserWarning"
    log_path = script.scratch_path / "pip.log"

    result = script.pip_install_local(
        "-vv",
        "--dry-run",
        "--no-deps",
        "--log",
        str(log_path),
        warning_project,
        find_links=[],
        build_isolation=True,
    )

    warning = "backend warning [bold] from metadata hook"
    assert warning not in result.stdout + result.stderr
    assert warning not in log_path.read_text()


DEPRECATION_TEXT = "drop support for Python 2.7"
CPYTHON_DEPRECATION_TEXT = "January 1st, 2020"


def test_version_warning_is_not_shown_if_python_version_is_not_2(
    script: PipTestEnvironment,
) -> None:
    result = script.pip("debug", allow_stderr_warning=True)
    assert DEPRECATION_TEXT not in result.stderr, str(result)
    assert CPYTHON_DEPRECATION_TEXT not in result.stderr, str(result)


def test_flag_does_nothing_if_python_version_is_not_2(
    script: PipTestEnvironment,
) -> None:
    script.pip("list", "--no-python-version-warning")
