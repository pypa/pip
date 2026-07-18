#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["pyte"]
# ///
"""Exercise pip's spinner through a pseudo-terminal.

Usage::

    uv run tools/benchmark_spinner_pty.py /path/to/python --label main
    uv run tools/benchmark_spinner_pty.py /path/to/python --label pr

The supplied Python executable must have pip installed. Run the command once
for each revision, then compare the reported terminal transcript metrics.
This is intentionally separate from the ASV benchmark: PTYs are not
available on every platform, and this measures terminal behavior rather than
just the spinner hot loop.
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

import pyte


CHILD = r"""
import logging
import sys
import time

from pip._internal.cli import spinners

spinners.logger.setLevel(logging.INFO)
with spinners.open_spinner("Building wheel") as spinner:
    end = time.monotonic() + float(sys.argv[1])
    while time.monotonic() < end:
        spinner.spin()
        time.sleep(0.0025)
"""


def run(python: Path, seconds: float) -> bytes:
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            [str(python), "-c", CHILD, str(seconds)],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env={**os.environ, "TERM": "xterm-256color", "COLUMNS": "100"},
        )
    finally:
        os.close(slave)

    chunks: list[bytes] = []
    try:
        while select.select([master], [], [], 20)[0]:
            try:
                chunk = os.read(master, 65536)
            except OSError:  # EIO is the normal PTY EOF on Linux.
                break
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(master)
    return b"".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python", type=Path)
    parser.add_argument("--label", default="run")
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args()

    started = time.monotonic()
    transcript = run(args.python, args.seconds)
    elapsed = time.monotonic() - started

    screen = pyte.Screen(100, 40)
    pyte.ByteStream(screen).feed(transcript)
    display = "\n".join(screen.display)
    result = {
        "label": args.label,
        "python": str(args.python),
        "seconds": args.seconds,
        "elapsed_seconds": round(elapsed, 3),
        "bytes_written": len(transcript),
        "erase_sequences": transcript.count(b"[2K"),
        "cursor_up_sequences": transcript.count(b"[1A"),
        "done_line_kept": "... done" in display,
    }
    print(json.dumps(result, indent=2))
    print("\nFinal terminal screen:\n" + display.rstrip())


if __name__ == "__main__":
    if os.name != "posix":
        raise SystemExit("This benchmark requires a POSIX pseudo-terminal.")
    main()
