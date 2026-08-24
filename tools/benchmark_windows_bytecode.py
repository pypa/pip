"""Compare wheel bytecode compilation across two local pip source trees.

Run this on Windows with real-time antivirus protection in its normal state.
The generated wheel, virtual environment, and installed files are temporary.
Results include exact installed-file comparisons as well as timings.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any


def record_digest(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def build_wheel(path: Path, source_count: int) -> None:
    files: dict[str, bytes] = {
        "benchpkg-1.0.dist-info/METADATA": (
            b"Metadata-Version: 2.1\nName: benchpkg\nVersion: 1.0\n"
        ),
        "benchpkg-1.0.dist-info/WHEEL": (
            b"Wheel-Version: 1.0\n"
            b"Generator: pip-review\n"
            b"Root-Is-Purelib: true\n"
            b"Tag: py3-none-any\n"
        ),
    }
    for index in range(source_count):
        files[f"benchpkg/module_{index:04d}.py"] = (
            f"VALUE = {index}\n"
            f"def calculate(value):\n"
            "    total = value\n"
            "    for offset in range(32):\n"
            f"        total = (total * 33 + offset + {index}) % 1000003\n"
            "    return total\n"
        ).encode()

    record_path = "benchpkg-1.0.dist-info/RECORD"
    rows = [
        (name, record_digest(data), str(len(data)))
        for name, data in sorted(files.items())
    ]
    rows.append((record_path, "", ""))
    record = io.StringIO(newline="")
    csv.writer(record, lineterminator="\n").writerows(rows)
    files[record_path] = record.getvalue().encode()

    timestamp = (2024, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)


def get_defender_status() -> dict[str, Any] | None:
    command = (
        "$s=Get-MpComputerStatus -ErrorAction SilentlyContinue;"
        "if($s){[pscustomobject]@{"
        "antivirusEnabled=$s.AntivirusEnabled;"
        "realTimeProtectionEnabled=$s.RealTimeProtectionEnabled;"
        "ioavProtectionEnabled=$s.IoavProtectionEnabled;"
        "behaviorMonitorEnabled=$s.BehaviorMonitorEnabled"
        "}|ConvertTo-Json -Compress}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
    )
    if result.returncode or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def benchmark(
    baseline: Path,
    candidate: Path,
    source_counts: list[int],
    runs: int,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pip-bytecode-benchmark-") as temp:
        root = Path(temp)
        wheel = root / "benchpkg-1.0-py3-none-any.whl"
        environment = root / "environment"
        subprocess.run([sys.executable, "-m", "venv", environment], check=True)
        python = environment / "Scripts" / "python.exe"
        site_packages = environment / "Lib" / "site-packages"
        package_dir = site_packages / "benchpkg"
        dist_info_dir = site_packages / "benchpkg-1.0.dist-info"

        def clear_install() -> None:
            shutil.rmtree(package_dir, ignore_errors=True)
            shutil.rmtree(dist_info_dir, ignore_errors=True)

        def snapshot() -> dict[str, str]:
            installed = {}
            for install_root in (package_dir, dist_info_dir):
                installed.update(
                    {
                        path.relative_to(site_packages)
                        .as_posix(): hashlib.sha256(path.read_bytes())
                        .hexdigest()
                        for path in sorted(install_root.rglob("*"))
                        if path.is_file()
                    }
                )
            return installed

        def install(source: Path, no_compile: bool) -> tuple[float, dict[str, str]]:
            clear_install()
            env = os.environ.copy()
            env.update(
                {
                    "PYTHONPATH": os.fspath(source / "src"),
                    "SOURCE_DATE_EPOCH": "1704067200",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_NO_COLOR": "1",
                    "PYTHONUTF8": "1",
                }
            )
            command = [
                os.fspath(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-cache-dir",
            ]
            if no_compile:
                command.append("--no-compile")
            command.append(os.fspath(wheel))
            started = time.perf_counter()
            result = subprocess.run(command, env=env, text=True, capture_output=True)
            elapsed = time.perf_counter() - started
            if result.returncode:
                raise RuntimeError(f"{result.stdout}\n{result.stderr}")
            return elapsed, snapshot()

        def measure(
            source_count: int, no_compile: bool, repetitions: int
        ) -> dict[str, Any]:
            build_wheel(wheel, source_count)
            install(baseline, no_compile)
            install(candidate, no_compile)
            timings: dict[str, list[float]] = {
                "baseline": [],
                "candidate": [],
            }
            snapshots: dict[str, list[dict[str, str]]] = {
                "baseline": [],
                "candidate": [],
            }
            sources = {"baseline": baseline, "candidate": candidate}
            order = ["baseline", "candidate", "candidate", "baseline"]
            while len(timings["baseline"]) < repetitions:
                for name in order:
                    if len(timings[name]) >= repetitions:
                        continue
                    elapsed, installed = install(sources[name], no_compile)
                    timings[name].append(elapsed)
                    snapshots[name].append(installed)

            reference = snapshots["baseline"][0]
            artifacts_equal = all(
                installed == reference
                for condition in snapshots.values()
                for installed in condition
            )
            baseline_median = statistics.median(timings["baseline"])
            candidate_median = statistics.median(timings["candidate"])
            return {
                "sourceCount": source_count,
                "noCompile": no_compile,
                "baselineSeconds": timings["baseline"],
                "candidateSeconds": timings["candidate"],
                "baselineMedian": baseline_median,
                "candidateMedian": candidate_median,
                "savedSeconds": baseline_median - candidate_median,
                "speedup": baseline_median / candidate_median,
                "artifactsEqual": artifacts_equal,
                "installedFileCount": len(reference),
            }

        compiled = [measure(count, False, runs) for count in source_counts]
        no_compile = measure(max(source_counts), True, max(3, runs // 2))
        return {
            "python": sys.version,
            "cpuCount": os.cpu_count(),
            "processCpuCount": getattr(os, "process_cpu_count", os.cpu_count)(),
            "defender": get_defender_status(),
            "compiled": compiled,
            "noCompileControl": no_compile,
        }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--baseline",
    type=Path,
    required=True,
    help="Baseline pip source tree.",
)
parser.add_argument(
    "--candidate",
    type=Path,
    required=True,
    help="Candidate pip source tree.",
)
parser.add_argument(
    "--counts",
    default="7,8,32,128,256,1200",
    help="Comma-separated Python source-file counts.",
)
parser.add_argument(
    "--runs",
    type=int,
    default=6,
    help="Measured runs per source tree and file count.",
)
args = parser.parse_args()
if sys.platform != "win32":
    parser.error("this benchmark targets Windows bytecode compilation")
for source_tree in (args.baseline, args.candidate):
    if not (source_tree / "src" / "pip").is_dir():
        parser.error(f"not a pip source tree: {source_tree}")
counts = [int(value) for value in args.counts.split(",")]
print(
    json.dumps(
        benchmark(args.baseline, args.candidate, counts, args.runs),
        separators=(",", ":"),
    )
)
