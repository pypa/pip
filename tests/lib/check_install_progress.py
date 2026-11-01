"""Exercise progress rendering in a fresh process with pip's import guard."""

import sys
import warnings
from io import StringIO

from pip._vendor import rich
from pip._vendor.rich.console import Console
from pip._vendor.rich.progress import Progress, TextColumn

from pip._internal.commands.install import (
    _eagerly_import_modules,
    _prevent_further_imports,
)
from pip._internal.utils.deprecation import PipDeprecationWarning


def main() -> None:
    output = StringIO()
    _eagerly_import_modules()
    _prevent_further_imports()
    loaded_modules = set(sys.modules)

    with warnings.catch_warnings():
        warnings.simplefilter("error", PipDeprecationWarning)
        console = Console(
            file=output,
            force_terminal=True,
            legacy_windows=False,
            color_system=None,
            width=40,
        )
        with Progress(
            TextColumn("{task.description}"), console=console, auto_refresh=False
        ) as progress:
            task = progress.add_task(":package: café", total=1)
            progress.update(task, completed=1)

    # Dynamic imports can bypass the audit hook's import event.
    late_rich_imports = {
        name
        for name in sys.modules.keys() - loaded_modules
        if name.startswith(f"{rich.__name__}.")
    }
    assert not late_rich_imports, late_rich_imports
    assert "📦 café" in output.getvalue()


if __name__ == "__main__":
    main()
