"""Interrupt an uninstall, wheel write or target relocation."""

import sys
from typing import Any

from pip._internal.cli.main import main


def interrupt_write(event: str, args: tuple[Any, ...]) -> None:
    suffixes: tuple[str, ...]
    if sys.argv[2] == "uninstall" and event == "os.rename":
        path = args[0]
        suffixes = ("/recoveryprobe/",)
    elif sys.argv[2] == "metadata" and event == "open" and args[1] == "w":
        path = args[0]
        suffixes = ("recoveryprobe-2.0.dist-info/METADATA",)
    elif sys.argv[2] in ("scripts", "rollback") and event == "os.rename":
        path = args[1]
        suffixes = ("recoveryprobe-2.0.dist-info/INSTALLER",)
        if sys.argv[2] == "rollback":
            suffixes += ("recoveryprobe-1.0.dist-info/",)
    elif sys.argv[2] == "target" and event == "shutil.move":
        path = args[0]
        suffixes = ("/recoveryprobe-2.0.dist-info",)
    else:
        return

    if isinstance(path, str) and path.replace("\\", "/").endswith(suffixes):
        __import__("wave")


assert "wave" not in sys.modules
sys.addaudithook(interrupt_write)
extra_args = (
    ["--target", sys.argv[3], "--upgrade"] if sys.argv[2] == "target" else sys.argv[3:]
)
sys.exit(
    main(
        [
            "install",
            "--no-index",
            "--no-compile",
            "--force-reinstall",
            sys.argv[1],
            *extra_args,
        ]
    )
)
