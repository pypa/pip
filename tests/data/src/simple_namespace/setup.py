from setuptools import setup

setup(
    name="simple_namespace",
    version="1.0",
    namespace_packages=["simple_namespace"],
    packages=["simple_namespace.module"],
)
