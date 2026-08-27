"""Reproduce free-threaded CPython serial-versus-threaded marshal differences.

Examples:
  python3.15t tools/repro_threaded_pyc_determinism.py --gil off \
      --output repro-gil-off --require-difference
  python3.15t tools/repro_threaded_pyc_determinism.py --gil on \
      --backend marshal --output repro-gil-on --require-difference

The script uses only the Python standard library. It creates identical source
files, compiles them in fresh serial and threaded child processes, compares the
resulting bytes, and preserves the first differing pair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import marshal
import os
import platform
import py_compile
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = '''from __future__ import annotations


def validate_values(values: Mapping[str, Any]) -> Mapping[str, Any]:
    if not values:
        raise ValidationError("At least one value must be provided")
    if not all(isinstance(item, str) for item in values.values()):
        raise ValidationError("Values must be strings")
    return values


class ValidationError(Exception):
    """Raised when input data is invalid."""

    context: str | None = None
    message: str

    def __init__(
        self,
        cause: str | Exception,
        *,
        context: str | None = None,
    ) -> None:
        if isinstance(cause, ValidationError):
            if cause.context:
                self.context = (
                    f"{context}.{cause.context}" if context else cause.context
                )
            else:
                self.context = context
            self.message = cause.message
        else:
            self.context = context
            self.message = str(cause)

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} in {self.context!r}"
        return self.message


class RequiredKeyError(ValidationError):
    def __init__(self, key: str) -> None:
        super().__init__("Missing required value", context=key)
'''


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def compile_one(
    source: Path,
    destination: Path,
    logical_name: str,
    backend: str,
) -> None:
    if backend == "py_compile":
        py_compile.compile(
            str(source),
            cfile=str(destination),
            dfile=logical_name,
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH,
        )
    else:
        code = compile(
            source.read_bytes(),
            logical_name,
            "exec",
            dont_inherit=True,
        )
        destination.write_bytes(marshal.dumps(code))


def compile_sources(
    sources: list[Path],
    destination: Path,
    *,
    threaded: bool,
    workers: int,
    backend: str,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    def compile_index(index: int) -> None:
        compile_one(
            sources[index],
            destination / f"module_{index:03}.pyc",
            f"/repro/module_{index:03}.py",
            backend,
        )

    if threaded:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(compile_index, range(len(sources))))
    else:
        for index in range(len(sources)):
            compile_index(index)


def compare_values(left: Any, right: Any, path: str, differences: list[str]) -> None:
    if isinstance(left, types.CodeType) and isinstance(right, types.CodeType):
        compare_code(left, right, path, differences)
    elif (
        isinstance(left, tuple) and isinstance(right, tuple) and len(left) == len(right)
    ):
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            compare_values(left_item, right_item, f"{path}[{index}]", differences)
    elif left != right:
        differences.append(path)


def compare_code(
    left: types.CodeType,
    right: types.CodeType,
    path: str,
    differences: list[str],
) -> None:
    fields = (
        "co_argcount",
        "co_posonlyargcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_stacksize",
        "co_flags",
        "co_code",
        "co_consts",
        "co_names",
        "co_varnames",
        "co_filename",
        "co_name",
        "co_qualname",
        "co_firstlineno",
        "co_linetable",
        "co_exceptiontable",
        "co_freevars",
        "co_cellvars",
    )
    for field in fields:
        compare_values(
            getattr(left, field),
            getattr(right, field),
            f"{path}.{field}",
            differences,
        )


def compare_outputs(
    serial_dir: Path,
    threaded_dir: Path,
    header_bytes: int,
) -> list[dict[str, Any]]:
    differences = []
    for serial_path in sorted(serial_dir.glob("*.pyc")):
        threaded_path = threaded_dir / serial_path.name
        serial = serial_path.read_bytes()
        threaded = threaded_path.read_bytes()
        if serial == threaded:
            continue
        semantic_differences: list[str] = []
        compare_code(
            marshal.loads(serial[header_bytes:]),
            marshal.loads(threaded[header_bytes:]),
            "code",
            semantic_differences,
        )
        changed_offsets = [
            index
            for index, (left, right) in enumerate(zip(serial, threaded))
            if left != right
        ]
        differences.append(
            {
                "file": serial_path.name,
                "serialSha256": hashlib.sha256(serial).hexdigest(),
                "threadedSha256": hashlib.sha256(threaded).hexdigest(),
                "serialBytes": len(serial),
                "threadedBytes": len(threaded),
                "headerBytes": header_bytes,
                "headersEqual": (
                    serial[:header_bytes] == threaded[:header_bytes]
                    if header_bytes
                    else None
                ),
                "differentByteCount": len(changed_offsets)
                + abs(len(serial) - len(threaded)),
                "firstDifferentOffsets": changed_offsets[:50],
                "semanticDifferences": semantic_differences[:100],
            }
        )
    return differences


def child_command(
    script: Path,
    mode: str,
    root: Path,
    workers: int,
    gil: str,
    backend: str,
) -> list[str]:
    command = [sys.executable]
    if gil != "default":
        command.extend(["-X", f"gil={1 if gil == 'on' else 0}"])
    command.extend(
        [
            os.fspath(script),
            "--child",
            mode,
            "--root",
            os.fspath(root),
            "--workers",
            str(workers),
            "--backend",
            backend,
        ]
    )
    return command


def run_child(args: argparse.Namespace) -> None:
    root = args.root
    sources = sorted((root / "sources").glob("*.py"))
    compile_sources(
        sources,
        root / args.child,
        threaded=args.child == "threaded",
        workers=args.workers,
        backend=args.backend,
    )
    print(
        json.dumps(
            {
                "mode": args.child,
                "gilEnabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
                "files": len(sources),
            },
            separators=(",", ":"),
        )
    )


def run_parent(args: argparse.Namespace) -> int:
    script = Path(__file__).resolve()
    temporary = None
    if args.output is None:
        temporary = tempfile.TemporaryDirectory(prefix="threaded-pyc-repro-")
        output = Path(temporary.name)
    else:
        output = args.output.resolve()
        if output.exists() and any(output.iterdir()):
            raise SystemExit(f"output directory is not empty: {output}")
        output.mkdir(parents=True, exist_ok=True)

    source_text = (
        args.fixture.read_text(encoding="utf-8")
        if args.fixture is not None
        else DEFAULT_SOURCE
    )
    sources = output / "sources"
    sources.mkdir()
    for index in range(args.files):
        (sources / f"module_{index:03}.py").write_text(source_text, encoding="utf-8")

    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": "1704067200",
            "PYTHONUTF8": "1",
        }
    )
    attempts = []
    first_difference = None
    for attempt in range(1, args.attempts + 1):
        serial_dir = output / "serial"
        threaded_dir = output / "threaded"
        shutil.rmtree(serial_dir, ignore_errors=True)
        shutil.rmtree(threaded_dir, ignore_errors=True)
        serial = subprocess.run(
            child_command(
                script,
                "serial",
                output,
                args.workers,
                args.gil,
                args.backend,
            ),
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        threaded = subprocess.run(
            child_command(
                script,
                "threaded",
                output,
                args.workers,
                args.gil,
                args.backend,
            ),
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        differences = compare_outputs(
            serial_dir,
            threaded_dir,
            16 if args.backend == "py_compile" else 0,
        )
        attempts.append(
            {
                "attempt": attempt,
                "serialChild": json.loads(serial.stdout),
                "threadedChild": json.loads(threaded.stdout),
                "differentFiles": len(differences),
            }
        )
        if differences:
            first_difference = differences
            pair = output / "first-difference"
            pair.mkdir()
            name = differences[0]["file"]
            shutil.copy2(serial_dir / name, pair / f"serial-{name}")
            shutil.copy2(threaded_dir / name, pair / f"threaded-{name}")
            break

    result = {
        "python": sys.version,
        "platform": platform.platform(),
        "availableCpuCount": getattr(os, "process_cpu_count", os.cpu_count)(),
        "freeThreadedBuild": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "requestedGil": args.gil,
        "backend": args.backend,
        "workers": args.workers,
        "files": args.files,
        "fixture": os.fspath(args.fixture) if args.fixture is not None else None,
        "reproduced": first_difference is not None,
        "attempts": attempts,
        "differences": first_difference or [],
        "output": os.fspath(output),
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    if temporary is not None:
        temporary.cleanup()
    return 0 if result["reproduced"] or not args.require_difference else 1


parser = argparse.ArgumentParser(
    description="Reproduce threaded py_compile byte differences without pip."
)
parser.add_argument("--child", choices=["serial", "threaded"], help=argparse.SUPPRESS)
parser.add_argument("--root", type=Path, help=argparse.SUPPRESS)
parser.add_argument("--workers", type=positive_int, default=8)
parser.add_argument("--files", type=positive_int, default=64)
parser.add_argument("--attempts", type=positive_int, default=10)
parser.add_argument("--gil", choices=["default", "on", "off"], default="default")
parser.add_argument(
    "--backend",
    choices=["py_compile", "marshal"],
    default="py_compile",
)
parser.add_argument("--fixture", type=Path)
parser.add_argument("--output", type=Path)
parser.add_argument("--require-difference", action="store_true")
arguments = parser.parse_args()

if arguments.child:
    if arguments.root is None:
        parser.error("--root is required in child mode")
    run_child(arguments)
else:
    raise SystemExit(run_parent(arguments))
