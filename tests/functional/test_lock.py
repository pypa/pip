import textwrap
from pathlib import Path
from typing import Any, Dict

from pip._internal.models.pylock import Pylock
from pip._internal.utils.compat import tomllib
from pip._internal.utils.urls import path_to_url

from ..lib import PipTestEnvironment, TestData


def _test_validation_and_roundtrip(pylock_dict: Dict[str, Any]) -> None:
    """Test that Pylock can be serialized and deserialized correctly."""
    pylock = Pylock.from_dict(pylock_dict)
    assert pylock.to_dict() == pylock_dict


def test_lock_wheel_from_findlinks(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    """Test locking a simple wheel package, to the default pylock.toml."""
    result = script.pip(
        "lock",
        "simplewheel==2.0",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        expect_stderr=True,  # for the experimental warning
    )
    result.did_create(Path("scratch") / "pylock.toml")
    pylock = tomllib.loads(script.scratch_path.joinpath("pylock.toml").read_text())
    assert pylock == {
        "created-by": "pip",
        "lock-version": "1.0",
        "packages": [
            {
                "name": "simplewheel",
                "version": "2.0",
                "wheels": [
                    {
                        "name": "simplewheel-2.0-1-py2.py3-none-any.whl",
                        "url": path_to_url(
                            str(
                                shared_data.root
                                / "packages"
                                / "simplewheel-2.0-1-py2.py3-none-any.whl"
                            )
                        ),
                        "hashes": {
                            "sha256": (
                                "71e1ca6b16ae3382a698c284013f6650"
                                "4f2581099b2ce4801f60e9536236ceee"
                            )
                        },
                    }
                ],
            },
        ],
    }
    _test_validation_and_roundtrip(pylock)


def test_lock_sdist_from_findlinks(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """Test locking a simple wheel package, to the default pylock.toml."""
    result = script.pip(
        "lock",
        "simple==2.0",
        "--no-binary=simple",
        "--quiet",
        "--output=-",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        expect_stderr=True,  # for the experimental warning
    )
    pylock = tomllib.loads(result.stdout)
    assert pylock["packages"] == [
        {
            "name": "simple",
            "sdist": {
                "hashes": {
                    "sha256": (
                        "3a084929238d13bcd3bb928af04f3bac"
                        "7ca2357d419e29f01459dc848e2d69a4"
                    ),
                },
                "name": "simple-2.0.tar.gz",
                "url": path_to_url(
                    str(shared_data.root / "packages" / "simple-2.0.tar.gz")
                ),
            },
            "version": "2.0",
        },
    ]
    _test_validation_and_roundtrip(pylock)


def test_lock_local_directory(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [project]
            name = "pkga"
            version = "1.0"
            """
        )
    )
    result = script.pip(
        "lock",
        ".",
        "--quiet",
        "--output=-",
        "--no-build-isolation",  # to use the pre-installed setuptools
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        cwd=project_path,
        expect_stderr=True,  # for the experimental warning
    )
    pylock = tomllib.loads(result.stdout)
    assert pylock["packages"] == [
        {
            "name": "pkga",
            "directory": {"path": "."},
        },
    ]
    _test_validation_and_roundtrip(pylock)


def test_lock_local_editable_with_dep(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [project]
            name = "pkga"
            version = "1.0"
            dependencies = ["simplewheel==2.0"]
            """
        )
    )
    result = script.pip(
        "lock",
        "-e",
        ".",
        "--quiet",
        "--output=-",
        "--no-build-isolation",  # to use the pre-installed setuptools
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        cwd=project_path,
        expect_stderr=True,  # for the experimental warning
    )
    pylock = tomllib.loads(result.stdout)
    assert pylock["packages"] == [
        {
            "name": "pkga",
            "directory": {"editable": True, "path": "."},
        },
        {
            "name": "simplewheel",
            "version": "2.0",
            "wheels": [
                {
                    "name": "simplewheel-2.0-1-py2.py3-none-any.whl",
                    "url": path_to_url(
                        str(
                            shared_data.root
                            / "packages"
                            / "simplewheel-2.0-1-py2.py3-none-any.whl"
                        )
                    ),
                    "hashes": {
                        "sha256": (
                            "71e1ca6b16ae3382a698c284013f6650"
                            "4f2581099b2ce4801f60e9536236ceee"
                        )
                    },
                }
            ],
        },
    ]
    _test_validation_and_roundtrip(pylock)


def test_lock_vcs(script: PipTestEnvironment, shared_data: TestData) -> None:
    result = script.pip(
        "lock",
        "git+https://github.com/pypa/pip-test-package@0.1.2",
        "--quiet",
        "--output=-",
        "--no-build-isolation",  # to use the pre-installed setuptools
        "--no-index",
        expect_stderr=True,  # for the experimental warning
    )
    pylock = tomllib.loads(result.stdout)
    assert pylock["packages"] == [
        {
            "name": "pip-test-package",
            "vcs": {
                "type": "git",
                "url": "https://github.com/pypa/pip-test-package",
                "requested-revision": "0.1.2",
                "commit-id": "f1c1020ebac81f9aeb5c766ff7a772f709e696ee",
            },
        },
    ]
    _test_validation_and_roundtrip(pylock)


def test_lock_archive(script: PipTestEnvironment, shared_data: TestData) -> None:
    result = script.pip(
        "lock",
        "https://github.com/pypa/pip-test-package/tarball/0.1.2",
        "--quiet",
        "--output=-",
        "--no-build-isolation",  # to use the pre-installed setuptools
        "--no-index",
        expect_stderr=True,  # for the experimental warning
    )
    pylock = tomllib.loads(result.stdout)
    assert pylock["packages"] == [
        {
            "name": "pip-test-package",
            "archive": {
                "url": "https://github.com/pypa/pip-test-package/tarball/0.1.2",
                "hashes": {
                    "sha256": (
                        "1b176298e5ecd007da367bfda91aad3c"
                        "4a6534227faceda087b00e5b14d596bf"
                    ),
                },
            },
        },
    ]
    _test_validation_and_roundtrip(pylock)
