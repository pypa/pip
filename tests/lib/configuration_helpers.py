"""Helpers for tests that check configuration
"""

import contextlib
import functools
import os
import tempfile
import textwrap
from typing import Any, Dict, Iterator

import pip._internal.configuration
from pip._internal.utils.misc import ensure_dir

# This is so that tests don't need to import pip._internal.configuration.
Kind = pip._internal.configuration.Kind
kinds = pip._internal.configuration.kinds


class ConfigurationMixin:
    def setup_method(self) -> None:
        self.configuration = pip._internal.configuration.Configuration(
            isolated=False,
        )

    def patch_configuration(self, variant: Kind, di: Dict[str, Any]) -> None:
        old = self.configuration._load_config_files

        @functools.wraps(old)
        def overridden() -> None:
            # Manual Overload
            self.configuration._config[variant].update(di)
            # Configuration._parsers has type:
            # Dict[Kind, List[Tuple[str, RawConfigParser]]].
            # As a testing convenience, pass a special value.
            self.configuration._parsers[variant].append(
                (None, None),  # type: ignore[arg-type]
            )
            old()

        # https://github.com/python/mypy/issues/2427
        self.configuration._load_config_files = overridden  # type: ignore[method-assign]

    @contextlib.contextmanager
    def tmpfile(self, contents: str) -> Iterator[str]:
        # Create a temporary file
        fd, path = tempfile.mkstemp(prefix="pip_", suffix="_config.ini", text=True)
        os.close(fd)

        contents = textwrap.dedent(contents).lstrip()
        ensure_dir(os.path.dirname(path))
        with open(path, "w") as f:
            f.write(contents)

        yield path

        os.remove(path)
