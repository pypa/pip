"""Keep a subprocess silent until the parent signals through a file."""

import sys
import time
from pathlib import Path

signal = Path(sys.argv[1])
deadline = time.monotonic() + 5
while not signal.exists():
    if time.monotonic() > deadline:
        sys.exit("parent did not signal")
    time.sleep(0.01)
