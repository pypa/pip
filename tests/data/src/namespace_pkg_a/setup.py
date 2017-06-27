from setuptools import find_packages, setup

setup(
    name='namespace-pkg-a',
    version='1.0.0',
    packages=['namespace.pkg_a'],
    namespace_packages=['namespace']
)
