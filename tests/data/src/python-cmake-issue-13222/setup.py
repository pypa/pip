import os
import shutil
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

HERE = Path(__file__).absolute().parent


class CMakeExtension(Extension):
    def __init__(self, name, source_dir=".", target=None, **kwargs):
        super().__init__(name, sources=[], **kwargs)
        self.source_dir = Path(source_dir).absolute()
        self.target = target if target is not None else name.rpartition(".")[-1]

    @classmethod
    def cmake_executable(cls):
        cmake = os.getenv("CMAKE_EXECUTABLE", "")
        if not cmake:
            cmake = shutil.which("cmake")
        return cmake


class cmake_build_ext(build_ext):
    def build_extension(self, ext):
        if not isinstance(ext, CMakeExtension):
            super().build_extension(ext)
            return

        cmake = ext.cmake_executable()
        if cmake is None:
            raise RuntimeError("Cannot find CMake executable.")

        self.spawn([cmake, "--version"])


setup(
    name="cmake-venv-test",
    version="0.0.1",
    cmdclass={"build_ext": cmake_build_ext},
    ext_modules=[CMakeExtension("cmake_venv_test._C", source_dir=HERE)],
)
