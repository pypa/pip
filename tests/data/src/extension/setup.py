from setuptools import Extension, setup

module = Extension("extension", sources=["extension.c"])
setup(name="extension", version="0.0.1", ext_modules=[module])
