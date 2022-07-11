import importlib.abc
import os
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from importlib.abc import Loader
from importlib.util import spec_from_file_location
from typing import Sequence, Union, Optional, List


class KeyringSubprocessFinder(importlib.abc.MetaPathFinder):
    @staticmethod
    def path():
        return Path(__file__).parent.parent / "_vendor"

    def __init__(self, *args, **kwargs):
        self._load_vendored_deps = False
        super().__init__(*args, **kwargs)

    def find_spec(
        self,
        fullname: str,
        paths: Optional[Sequence[Union[bytes, str]]],
        target: Optional[types.ModuleType] = ...,
    ) -> Optional[ModuleSpec]:
        location = self.location(fullname.split("."))

        if not location:
            return None

        spec = spec_from_file_location(fullname, location)
        spec.loader = KeyringSubprocessLoader(spec.loader)

        return spec

    def location(self, segments: List[str]) -> Optional[Path]:
        if segments[0] == "keyring":
            self._load_vendored_deps = sys.version_info < (3, 10)
        elif self._load_vendored_deps:
            pass
        else:
            return None

        segments, files = (
            segments[:-1],
            [
                f"{segments[-1]}{os.sep}__init__.py",
                f"{segments[-1]}.py",
            ],
        )
        location = self.path()

        for segment in segments:
            location = location / segment
            if not location.exists():
                return None

        for file in files:
            file = location / file
            if file.exists():
                return file

        return None


class KeyringSubprocessLoader(Loader):
    def __init__(self, loader):
        self.loader = loader

    def __getattr__(self, item):
        return getattr(self.loader, item)

    def exec_module(self, module: types.ModuleType) -> None:
        self.loader.exec_module(module)
        if module.__name__ == "keyring":
            from pip._vendor.keyring.backends.chainer import ChainerBackend

            ChainerBackend()
