"""Wheel inspection, hashing, and 300/10,000-file archive operations."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pip._internal.metadata import get_wheel_distribution
from pip._internal.metadata.base import FilesystemWheel
from pip._internal.models.scheme import Scheme
from pip._internal.operations.install.wheel import install_wheel
from pip._internal.utils.misc import hash_file
from pip._internal.utils.unpacking import untar_file, unzip_file
from pip._internal.utils.wheel import parse_wheel

from ._support import make_sdist, make_wheel


@pytest.fixture(scope="session", params=[300, 10_000], ids=["300-files", "10000-files"])
def archives(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path, int]:
    root = tmp_path_factory.mktemp("archives")
    count = request.param
    return (
        make_wheel(root, "payload-pkg", "1.0.0", payload_files=count),
        make_sdist(root, "payload-pkg", "1.0.0", payload_files=count),
        count,
    )


def test_read_metadata(
    benchmark: BenchmarkFixture, archives: tuple[Path, Path, int]
) -> None:
    wheel, _, _ = archives
    dist = benchmark(get_wheel_distribution, FilesystemWheel(str(wheel)), "payload-pkg")
    assert dist.canonical_name == "payload-pkg"
    assert str(dist.version) == "1.0.0"


def test_validate_wheel(
    benchmark: BenchmarkFixture, archives: tuple[Path, Path, int]
) -> None:
    wheel, _, _ = archives

    def validate() -> str:
        with ZipFile(wheel) as archive:
            return parse_wheel(archive, "payload-pkg")[0]

    assert benchmark(validate) == "payload_pkg-1.0.0.dist-info"


def test_hash_wheel(
    benchmark: BenchmarkFixture, archives: tuple[Path, Path, int]
) -> None:
    wheel, _, _ = archives
    digest, size = benchmark(hash_file, str(wheel))
    assert size == wheel.stat().st_size
    assert len(digest.hexdigest()) == 64


@pytest.mark.parametrize("operation", ["unzip", "untar", "install", "install-bytecode"])
def test_materialize_archive(
    benchmark: BenchmarkFixture,
    archives: tuple[Path, Path, int],
    operation: str,
    tmp_path: Path,
) -> None:
    wheel, sdist, count = archives
    target = tmp_path / "output"

    def setup() -> None:
        assert not target.exists()

    def materialize() -> None:
        if operation == "unzip":
            unzip_file(str(wheel), str(target), flatten=False)
        elif operation == "untar":
            untar_file(str(sdist), str(target))
        else:
            scheme = Scheme(
                str(target),
                str(target),
                str(target / "include"),
                str(target / "bin"),
                str(target),
            )
            install_wheel(
                "payload-pkg",
                str(wheel),
                scheme,
                "payload-pkg==1.0.0",
                pycompile=operation == "install-bytecode",
                warn_script_location=False,
            )

    def teardown() -> None:
        try:
            if operation.startswith("install"):
                record = target / "payload_pkg-1.0.0.dist-info" / "RECORD"
                with record.open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.reader(stream))
                assert len(rows) >= count + 4
                assert all((target / row[0]).is_file() for row in rows)
            else:
                assert sum(path.is_file() for path in target.rglob("*")) >= count
        finally:
            shutil.rmtree(target, ignore_errors=True)

    try:
        benchmark.pedantic(
            materialize, setup=setup, teardown=teardown, rounds=3, iterations=1
        )
        # pytest-benchmark's disabled mode calls setup/target, but not teardown.
        if target.exists():
            teardown()
    finally:
        shutil.rmtree(target, ignore_errors=True)
